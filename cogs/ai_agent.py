import asyncio
import difflib
import io
import os
import shutil
import sys
import textwrap
import traceback
from datetime import datetime, timezone
import discord
from discord.ext import commands
from google import genai
from utils import DB_FILE, get_db, MAIN_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARN_COLOR, INFO_COLOR

class AIAgent(commands.Cog):
    """Autonomous AI Agent for real-time Discord code modification and zero-shot dynamic actions."""

    def __init__(self, bot):
        self.bot = bot
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini = genai.Client(api_key=gemini_key).aio if gemini_key else None
        self.backup_history = {}  # filepath -> backup_path

    async def _call_gemini(self, prompt: str, system_instruction: str = "") -> str:
        if not self.gemini:
            raise Exception("Gemini API client is not configured. Please set GEMINI_API_KEY.")
        contents = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        for model_name in ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash"]:
            try:
                res = await self.gemini.models.generate_content(
                    model=model_name,
                    contents=contents,
                )
                if res and res.text:
                    return res.text.strip()
            except Exception:
                continue
        raise Exception("All Gemini models failed to generate response.")

    def _clean_code_fence(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            return "\n".join(lines).strip()
        return text

    async def is_bot_admin(self, user) -> bool:
        """Helper to reliably check if a user is the bot owner or team member."""
        if await self.bot.is_owner(user):
            return True
        try:
            app_info = await self.bot.application_info()
            if app_info.team:
                if any(m.id == user.id for m in app_info.team.members):
                    return True
            elif app_info.owner and app_info.owner.id == user.id:
                return True
        except Exception:
            pass
        return False

    # =========================================================================
    # 🛠️ 1. CHAT-TO-CODE AUTONOMOUS MODIFIER (&patch, &modify, &autocode)
    # =========================================================================

    @commands.command(name="patch", aliases=["modify", "autocode", "codeagent"], description="[Owner] Give a natural language prompt to modify or create bot code live")
    async def patch_code(self, ctx, *, instruction: str):
        """Owner command to modify or create code files via AI prompt, validate syntax, and hot-reload."""
        if not await self.is_bot_admin(ctx.author):
            return await ctx.reply("🔒 **Restricted:** The `&patch` code modifier is exclusive to the Bot Creator / Team.")

        msg = await ctx.reply("🔍 **AI Code Agent:** Analyzing repository structure and prompt...")

        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        cogs_dir = os.path.join(base_dir, "cogs")
        all_cogs = [f for f in os.listdir(cogs_dir) if f.endswith(".py") and not f.startswith("__")]

        file_list_str = "\n".join([f"- cogs/{f}" for f in all_cogs] + ["- utils.py", "- main.py"])

        routing_prompt = f"""
Given the user's coding instruction for a discord.py bot:
"{instruction}"

Available files in repository:
{file_list_str}

Respond with JSON only:
{{
  "target_file": "relative/path/to/file.py",
  "is_new_file": false,
  "cog_name": "cog_module_name_or_none",
  "reasoning": "brief 1 sentence reasoning"
}}
"""
        try:
            route_res = await self._call_gemini(
                routing_prompt,
                system_instruction="You are an autonomous senior Python architect. Output strictly JSON without markdown."
            )
            # Parse JSON
            clean_json = self._clean_code_fence(route_res)
            import json
            route_data = json.loads(clean_json)
            rel_path = route_data.get("target_file", "cogs/custom_commands.py").replace("\\", "/")
            is_new = route_data.get("is_new_file", False)
            cog_name = route_data.get("cog_name")
        except Exception:
            rel_path = "cogs/custom_commands.py"
            is_new = False
            cog_name = "custom_commands"

        target_abs = os.path.abspath(os.path.join(base_dir, rel_path))
        if not target_abs.startswith(base_dir):
            return await msg.edit(content="❌ **Security Violation:** Target file path outside project directory.")

        original_code = ""
        if os.path.exists(target_abs):
            with open(target_abs, "r", encoding="utf-8") as f:
                original_code = f.read()

        await msg.edit(content=f"🧠 **AI Code Agent:** Generating patch for `{rel_path}` with Gemini 3.6...")

        system_prompt = """You are an expert Discord.py v2+ bot engineer.
Rules:
1. Write 100% valid, production-ready, clean Python 3.10+ code.
2. Use discord.py 2.0+ async/await syntax (e.g. @commands.command or @commands.hybrid_command, ctx.reply/ctx.send, embeds with MAIN_COLOR/SUCCESS_COLOR/ERROR_COLOR from utils).
3. If modifying an existing Cog file, maintain all existing working commands unless asked to change them, and ensure `async def setup(bot): await bot.add_cog(CogName(bot))` is at the end.
4. Output ONLY the complete, drop-in Python source code for the file. DO NOT include explanation or markdown commentary outside code fences.
"""

        user_content = f"""Target File: {rel_path}
Is New File: {is_new}

User Instruction:
{instruction}

Current File Content:
```python
{original_code if original_code else '# New File'}
```

Return the complete updated file content in ```python ... ```:"""

        try:
            ai_response = await self._call_gemini(user_content, system_instruction=system_prompt)
            new_code = self._clean_code_fence(ai_response)
        except Exception as e:
            return await msg.edit(content=f"❌ **AI Generation Error:** {e}")

        # Backup existing file
        if os.path.exists(target_abs):
            bak_path = f"{target_abs}.bak_{int(datetime.now().timestamp())}"
            shutil.copyfile(target_abs, bak_path)
            self.backup_history[target_abs] = bak_path

        # Validate Python syntax before saving
        try:
            compile(new_code, target_abs, "exec")
        except SyntaxError as syn_err:
            return await msg.edit(content=f"❌ **Syntax Check Failed:**\n```py\n{syn_err}\nLine {syn_err.lineno}: {syn_err.text}\n```\nNo changes were applied.")

        # Write to disk
        os.makedirs(os.path.dirname(target_abs), exist_ok=True)
        with open(target_abs, "w", encoding="utf-8") as f:
            f.write(new_code)

        # Hot-reload if it is a Cog
        reload_status = "Skipped (Not a Cog)"
        if "cogs" in rel_path and rel_path.endswith(".py"):
            mod_name = f"cogs.{os.path.basename(rel_path)[:-3]}"
            try:
                if mod_name in self.bot.extensions:
                    await self.bot.reload_extension(mod_name)
                    reload_status = f"✅ Hot-reloaded `{mod_name}`"
                else:
                    await self.bot.load_extension(mod_name)
                    reload_status = f"✅ Loaded new extension `{mod_name}`"
            except Exception as reload_err:
                # Rollback on reload failure
                if target_abs in self.backup_history and os.path.exists(self.backup_history[target_abs]):
                    shutil.copyfile(self.backup_history[target_abs], target_abs)
                    try:
                        await self.bot.reload_extension(mod_name)
                    except Exception:
                        pass
                return await msg.edit(content=f"❌ **Cog Reload Error (Auto-Rolled Back):**\n```py\n{reload_err}\n```")

        # Generate Diff preview
        diff = list(difflib.unified_diff(
            original_code.splitlines(),
            new_code.splitlines(),
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
            n=2
        ))
        diff_text = "\n".join(diff[:25])
        if len(diff) > 25:
            diff_text += f"\n...({len(diff) - 25} more lines modified)"

        embed = discord.Embed(
            title="⚡ Code Patch Successfully Applied & Loaded!",
            description=f"**Target File:** `{rel_path}`\n**Status:** {reload_status}",
            color=SUCCESS_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="📝 Instruction", value=f"*{instruction[:300]}*", inline=False)
        if diff_text:
            embed.add_field(name="🔍 Code Diff Summary", value=f"```diff\n{diff_text[:950]}\n```", inline=False)
        embed.set_footer(text=f"Vortex Autonomous Engine • Use &rollback to undo")
        await msg.edit(content=None, embed=embed)

    # =========================================================================
    # ⏪ 2. ROLLBACK COMMAND (&rollback)
    # =========================================================================

    @commands.command(name="rollback", description="[Owner] Revert the last applied AI patch")
    async def rollback_patch(self, ctx, target_file: str = None):
        """Rollback the last file modified by &patch."""
        if not await self.is_bot_admin(ctx.author):
            return await ctx.reply("🔒 **Restricted:** Exclusive to the Bot Creator / Team.")

        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

        if not target_file:
            if not self.backup_history:
                return await ctx.reply("❌ No backup history found in this session.")
            target_abs, bak_path = list(self.backup_history.items())[-1]
        else:
            target_abs = os.path.abspath(os.path.join(base_dir, target_file))
            bak_path = self.backup_history.get(target_abs)

        if not bak_path or not os.path.exists(bak_path):
            return await ctx.reply(f"❌ No backup available for `{os.path.relpath(target_abs, base_dir)}`.")

        try:
            shutil.copyfile(bak_path, target_abs)
            rel_path = os.path.relpath(target_abs, base_dir)
            if "cogs" in rel_path and rel_path.endswith(".py"):
                mod_name = f"cogs.{os.path.basename(rel_path)[:-3]}"
                if mod_name in self.bot.extensions:
                    await self.bot.reload_extension(mod_name)
            await ctx.reply(f"✅ Successfully rolled back `{rel_path}` to previous version.")
        except Exception as e:
            await ctx.reply(f"❌ Error during rollback: {e}")

    # =========================================================================
    # ⚡ 3. ZERO-SHOT DYNAMIC ACTION RUNNER (&do, &run, &action)
    # =========================================================================

    @commands.command(name="do", aliases=["run", "action", "execute_ai"], description="Execute any Discord action on the fly even if no command exists")
    async def dynamic_do(self, ctx, *, action_prompt: str):
        """Zero-shot AI action runner that synthesizes and executes Discord actions dynamically."""
        is_owner = await self.is_bot_admin(ctx.author)
        is_admin = bool(ctx.guild and ctx.author.guild_permissions.administrator)

        if not (is_owner or is_admin):
            return await ctx.reply("🔒 **Permission Denied:** The `&do` dynamic action engine is reserved for Server Admins and the Bot Owner.")

        msg = await ctx.reply("⚡ **Vortex Dynamic AI:** Formulating action plan...")

        # Server context snapshot
        guild_info = f"Guild: {ctx.guild.name} (ID: {ctx.guild.id})" if ctx.guild else "Direct Message"
        roles_sample = [r.name for r in ctx.guild.roles[1:10]] if ctx.guild else []
        channels_sample = [c.name for c in ctx.guild.text_channels[:10]] if ctx.guild else []

        system_instruction = f"""You are an autonomous Discord AI executor for discord.py 2.0+.
Task: Convert the user's prompt into an async Python function `async def run(ctx, bot, db, discord, embed_color):` to execute the action.

Available Globals & Arguments in `run()`:
- `ctx`: Discord commands.Context
- `bot`: commands.Bot instance
- `db`: sqlite3 connection from get_db()
- `discord`: discord module
- `embed_color`: default brand color

Safety & Scope Rules:
- User is {'BOT OWNER (Full Access)' if is_owner else 'SERVER ADMIN (Guild-scoped actions only)'}.
- If Server Admin: ONLY perform server operations on `ctx.guild` (channels, roles, messages, kicks, bans, timeouts, embeds, server economy/stats). DO NOT access OS files, subprocess, or bot tokens.
- Return a summary string or discord.Embed to reply to the user.
- If creating channels, roles, or messages, handle potential Discord API errors with try/except.
- Output ONLY python code inside ```python ... ``` without commentary.
"""

        user_content = f"""Server Context:
- {guild_info}
- Existing Channels (Sample): {', '.join(channels_sample)}
- Existing Roles (Sample): {', '.join(roles_sample)}
- Author: {ctx.author} (ID: {ctx.author.id})
- Channel: #{getattr(ctx.channel, 'name', 'DM')}

User Instruction:
{action_prompt}

Generate the `run` async function:"""

        try:
            ai_code = await self._call_gemini(user_content, system_instruction=system_instruction)
            cleaned_code = self._clean_code_fence(ai_code)
        except Exception as e:
            return await msg.edit(content=f"❌ **AI Synthesis Error:** {e}")

        # Setup sandbox environment
        env = {
            "ctx": ctx,
            "bot": self.bot,
            "db": get_db(),
            "discord": discord,
            "embed_color": MAIN_COLOR,
            "asyncio": asyncio,
            "datetime": datetime,
            "timezone": timezone,
            "SUCCESS_COLOR": SUCCESS_COLOR,
            "ERROR_COLOR": ERROR_COLOR,
            "MAIN_COLOR": MAIN_COLOR,
        }

        # Block dangerous builtins and sensitive bot internals for non-owner
        if not is_owner:
            blocked_keywords = [
                "import os", "import sys", "import subprocess", "open(", "__import__",
                "eval(", "exec(", "shutil", "token", "DISCORD_TOKEN", "getenv", "environ",
                "globals()", "locals()", "getattr", "setattr", "delattr", "bot.http",
                "bot._connection", "exit(", "quit("
            ]
            if any(b in cleaned_code for b in blocked_keywords):
                return await msg.edit(content="🛡️ **Security Sandbox Blocked:** Action contains unauthorized system-level calls.")

        stdout = io.StringIO()
        try:
            exec(cleaned_code, env)
            run_func = env.get("run")
            if not run_func or not callable(run_func):
                return await msg.edit(content="❌ Failed to synthesize executable `run` function.")

            sys.stdout = stdout
            # Run with 15s timeout
            result = await asyncio.wait_for(
                run_func(ctx=ctx, bot=self.bot, db=get_db(), discord=discord, embed_color=MAIN_COLOR),
                timeout=15.0
            )
            out_logs = stdout.getvalue().strip()
        except asyncio.TimeoutError:
            return await msg.edit(content="⏱️ **Action Timed Out:** The dynamic execution exceeded 15 seconds.")
        except Exception:
            err_trace = traceback.format_exc()
            return await msg.edit(content=f"❌ **Execution Error:**\n```py\n{err_trace[-1200:]}\n```")
        finally:
            sys.stdout = sys.__stdout__

        # Render response
        if isinstance(result, discord.Embed):
            await msg.edit(content=None, embed=result)
        elif isinstance(result, str) and result.strip():
            embed = discord.Embed(
                title="⚡ Dynamic Action Completed",
                description=result[:2000],
                color=SUCCESS_COLOR,
                timestamp=datetime.now(timezone.utc),
            )
            if out_logs:
                embed.add_field(name="📋 Execution Logs", value=f"```\n{out_logs[:800]}\n```", inline=False)
            await msg.edit(content=None, embed=embed)
        else:
            desc = out_logs if out_logs else "Action executed successfully with no return output."
            embed = discord.Embed(
                title="⚡ Dynamic Action Completed",
                description=f"```\n{desc[:1900]}\n```",
                color=SUCCESS_COLOR,
            )
            await msg.edit(content=None, embed=embed)

    # =========================================================================
    # 🔍 4. CODE INSPECTION COMMANDS (&viewcode, &cogs)
    # =========================================================================

    @commands.command(name="viewcode", description="[Owner] View lines of code from any bot file")
    async def view_code(self, ctx, filepath: str, start: int = 1, end: int = 60):
        """View code directly from Discord."""
        if not await self.is_bot_admin(ctx.author):
            return await ctx.reply("🔒 **Restricted:** Exclusive to the Bot Creator / Team.")

        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        target_abs = os.path.abspath(os.path.join(base_dir, filepath))
        if not target_abs.startswith(base_dir) or not os.path.exists(target_abs):
            return await ctx.reply("❌ File not found or access denied.")

        with open(target_abs, "r", encoding="utf-8") as f:
            lines = f.readlines()

        total = len(lines)
        start_idx = max(0, start - 1)
        end_idx = min(total, end)
        snippet = "".join(lines[start_idx:end_idx])

        if len(snippet) > 1800:
            snippet = snippet[:1800] + "\n...[Truncated]"

        await ctx.reply(f"📄 **`{filepath}` (Lines {start}-{end_idx} of {total}):**\n```py\n{snippet}\n```")

    @commands.command(name="cogs", description="[Owner] List all loaded and available cogs")
    async def list_cogs(self, ctx):
        """List all active and available cogs."""
        if not await self.is_bot_admin(ctx.author):
            return await ctx.reply("🔒 **Restricted:** Exclusive to the Bot Creator / Team.")

        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        cogs_dir = os.path.join(base_dir, "cogs")
        all_cogs = sorted([f[:-3] for f in os.listdir(cogs_dir) if f.endswith(".py") and not f.startswith("__")])

        loaded_cogs = [k.replace("cogs.", "") for k in self.bot.extensions.keys() if k.startswith("cogs.")]

        lines = []
        for c in all_cogs:
            status = "🟢 Active" if c in loaded_cogs else "⚪ Unloaded"
            lines.append(f"`{c}` — {status}")

        embed = discord.Embed(
            title=f"🧩 Vortex Modular Cogs ({len(loaded_cogs)}/{len(all_cogs)} Loaded)",
            description="\n".join(lines),
            color=MAIN_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="Use &patch to edit or &reloadcog <cog> to reload")
        await ctx.reply(embed=embed)

    @commands.command(name="reloadcog", description="[Owner] Hot reload a specific cog")
    async def reload_cog_cmd(self, ctx, cog_name: str):
        """Hot reload a specific cog."""
        if not await self.is_bot_admin(ctx.author):
            return await ctx.reply("🔒 **Restricted:** Exclusive to the Bot Creator / Team.")

        cog_name = cog_name.replace("cogs.", "")
        full_name = f"cogs.{cog_name}"
        try:
            if full_name in self.bot.extensions:
                await self.bot.reload_extension(full_name)
                await ctx.reply(f"✅ Successfully reloaded `{full_name}`.")
            else:
                await self.bot.load_extension(full_name)
                await ctx.reply(f"✅ Successfully loaded `{full_name}`.")
        except Exception as e:
            await ctx.reply(f"❌ Error reloading `{full_name}`:\n```py\n{e}\n```")


# =========================================================================
# 🔘 INTERACTIVE DYNAMIC AI RUN BUTTON VIEW
# =========================================================================

class DynamicAIActionView(discord.ui.View):
    def __init__(self, bot, author_id: int, prompt: str):
        super().__init__(timeout=60)
        self.bot = bot
        self.author_id = author_id
        self.prompt = prompt

    @discord.ui.button(label="⚡ Run with Dynamic AI", style=discord.ButtonStyle.primary, emoji="🤖")
    async def run_ai_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ Only the command author can trigger this action.", ephemeral=True)

        self.stop()
        button.disabled = True
        button.label = "Executing Action..."
        await interaction.response.edit_message(view=self)

        ctx = await self.bot.get_context(interaction.message)
        cog = self.bot.get_cog("AIAgent")
        if cog:
            await cog.dynamic_do(ctx, action_prompt=self.prompt)
        else:
            await interaction.followup.send("❌ AIAgent cog is not currently loaded.")


async def setup(bot):
    await bot.add_cog(AIAgent(bot))
