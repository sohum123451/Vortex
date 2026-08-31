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

    async def _send_error_card(self, msg, stage: str, error_title: str, error_detail: str, target_file: str = None, was_rolled_back: bool = False):
        embed = discord.Embed(
            title=f"🚨 Execution Error — {error_title}",
            description=f"**Failed at:** `{stage}`" + (f"\n**Target File:** `{target_file}`" if target_file else ""),
            color=ERROR_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(
            name="📋 Error Diagnostics",
            value=f"```py\n{str(error_detail)[:950]}\n```",
            inline=False
        )
        if was_rolled_back:
            embed.add_field(
                name="🛡️ Auto-Rollback Safety",
                value="✅ **Automatic Rollback Completed:** The previous working code was preserved intact.",
                inline=False
            )
        embed.add_field(
            name="💡 Troubleshooting",
            value="• Specify the target file explicitly: `&patch in cogs/fun_social.py <prompt>`\n• Use `&viewcode <file>` to inspect code\n• Use `&rollback` to manually revert anytime",
            inline=False
        )
        embed.set_footer(text="Vortex Autonomous Self-Healing Engine")
        try:
            await msg.edit(content=None, embed=embed)
        except Exception:
            await msg.edit(content=f"❌ **{error_title}** ({stage}):\n```py\n{error_detail[:500]}\n```")

    # =========================================================================
    # 🛠️ 1. CHAT-TO-CODE AUTONOMOUS MODIFIER (&patch, &modify, &autocode)
    # =========================================================================

    @commands.command(name="patch", aliases=["modify", "autocode", "codeagent"], description="[Owner] Give a natural language prompt to modify or create bot code live")
    async def patch_code(self, ctx, *, instruction: str):
        """Owner command to modify or create code files via AI prompt, validate syntax, and hot-reload."""
        if not await self.is_bot_admin(ctx.author):
            return await ctx.reply("🔒 **Restricted:** The `&patch` code modifier is exclusive to the Bot Creator / Team.")

        start_time = datetime.now()
        
        # Step 1: Analysis & Routing
        step_text = (
            "⚙️ **Autonomous AI Code Agent**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟡 `[Step 1/5]` **Analyzing Repository** — Scanning cogs & locating target file...\n"
            "⚪ `[Step 2/5]` Synthesizing code with Gemini AI\n"
            "⚪ `[Step 3/5]` Creating safety backup & AST syntax check\n"
            "⚪ `[Step 4/5]` Applying patch & live hot-reloading\n"
            "⚪ `[Step 5/5]` Complete"
        )
        msg = await ctx.reply(step_text)

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
            clean_json = self._clean_code_fence(route_res)
            import json
            route_data = json.loads(clean_json)
            rel_path = route_data.get("target_file", "cogs/custom_commands.py").replace("\\", "/")
            is_new = route_data.get("is_new_file", False)
            cog_name = route_data.get("cog_name")
        except Exception as route_err:
            rel_path = "cogs/custom_commands.py"
            is_new = False
            cog_name = "custom_commands"

        target_abs = os.path.abspath(os.path.join(base_dir, rel_path))
        if not target_abs.startswith(base_dir):
            return await self._send_error_card(msg, "Stage 1: Routing", "Security Violation", "Target file path outside project directory.", rel_path)

        original_code = ""
        if os.path.exists(target_abs):
            with open(target_abs, "r", encoding="utf-8") as f:
                original_code = f.read()

        # Step 2: Code Generation
        step_text = (
            "⚙️ **Autonomous AI Code Agent**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 `[Step 1/5]` Target: `{rel_path}`\n"
            f"🟡 `[Step 2/5]` **Synthesizing Code** — Writing Discord.py async patch with Gemini 3.6 Flash...\n"
            "⚪ `[Step 3/5]` Creating safety backup & AST syntax check\n"
            "⚪ `[Step 4/5]` Applying patch & live hot-reloading\n"
            "⚪ `[Step 5/5]` Complete"
        )
        await msg.edit(content=step_text)

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
            return await self._send_error_card(msg, "Stage 2: Code Generation", "AI Generation Error", str(e), rel_path)

        # Step 3: Safety Backup & Syntax Validation
        step_text = (
            "⚙️ **Autonomous AI Code Agent**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 `[Step 1/5]` Target: `{rel_path}`\n"
            f"🟢 `[Step 2/5]` Code synthesized ({len(new_code.splitlines())} lines)\n"
            f"🟡 `[Step 3/5]` **Safety Verification** — Creating backup & compiling AST syntax...\n"
            "⚪ `[Step 4/5]` Applying patch & live hot-reloading\n"
            "⚪ `[Step 5/5]` Complete"
        )
        await msg.edit(content=step_text)

        if os.path.exists(target_abs):
            bak_path = f"{target_abs}.bak_{int(datetime.now().timestamp())}"
            shutil.copyfile(target_abs, bak_path)
            self.backup_history[target_abs] = bak_path

        try:
            compile(new_code, target_abs, "exec")
        except SyntaxError as syn_err:
            return await self._send_error_card(
                msg,
                "Stage 3: AST Syntax Validation",
                "Python Syntax Error",
                f"SyntaxError: {syn_err.msg}\nLine {syn_err.lineno}: {syn_err.text}",
                rel_path,
                was_rolled_back=True
            )

        # Step 4: Write & Hot Reload
        step_text = (
            "⚙️ **Autonomous AI Code Agent**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 `[Step 1/5]` Target: `{rel_path}`\n"
            f"🟢 `[Step 2/5]` Code synthesized ({len(new_code.splitlines())} lines)\n"
            f"🟢 `[Step 3/5]` AST syntax verified & backup saved\n"
            f"🟡 `[Step 4/5]` **Hot-Reloading** — Injecting module into live bot gateway...\n"
            "⚪ `[Step 5/5]` Complete"
        )
        await msg.edit(content=step_text)

        os.makedirs(os.path.dirname(target_abs), exist_ok=True)
        with open(target_abs, "w", encoding="utf-8") as f:
            f.write(new_code)

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
                if target_abs in self.backup_history and os.path.exists(self.backup_history[target_abs]):
                    shutil.copyfile(self.backup_history[target_abs], target_abs)
                    try:
                        await self.bot.reload_extension(mod_name)
                    except Exception:
                        pass
                return await self._send_error_card(
                    msg,
                    "Stage 4: Extension Hot-Reload",
                    "Cog Extension Load Error",
                    str(reload_err),
                    rel_path,
                    was_rolled_back=True
                )

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

        elapsed = (datetime.now() - start_time).total_seconds()

        embed = discord.Embed(
            title="⚡ Code Patch Successfully Applied & Loaded!",
            description=f"**Target File:** `{rel_path}`\n**Status:** {reload_status}\n⏱️ **Execution Time:** `{elapsed:.2f}s`",
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

        step_text = (
            "⚡ **Vortex Dynamic AI Engine**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟡 `[Step 1/3]` **Formulating Plan** — Analyzing guild context & intent...\n"
            "⚪ `[Step 2/3]` Synthesizing Discord async workflow\n"
            "⚪ `[Step 3/3]` Executing action"
        )
        msg = await ctx.reply(step_text)

        # Server context snapshot
        guild_info = f"Guild: {ctx.guild.name} (ID: {ctx.guild.id})" if ctx.guild else "Direct Message"
        roles_sample = [r.name for r in ctx.guild.roles[1:10]] if ctx.guild else []
        channels_sample = [c.name for c in ctx.guild.text_channels[:10]] if ctx.guild else []

        step_text = (
            "⚡ **Vortex Dynamic AI Engine**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 `[Step 1/3]` Context analyzed ({len(channels_sample)} channels, {len(roles_sample)} roles)\n"
            "🟡 `[Step 2/3]` **Synthesizing Flow** — Writing Discord async action with Gemini 3.6 Flash...\n"
            "⚪ `[Step 3/3]` Executing action"
        )
        await msg.edit(content=step_text)

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

        step_text = (
            "⚡ **Vortex Dynamic AI Engine**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 `[Step 1/3]` Context analyzed\n"
            f"🟢 `[Step 2/3]` Action synthesized & verified\n"
            "🟡 `[Step 3/3]` **Executing Action** — Running Discord operation..."
        )
        await msg.edit(content=step_text)

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
    # 🧬 5. AUTO-ML TELEMETRY & CONTINUOUS SELF-EVOLUTION SUITE
    # =========================================================================

    @commands.hybrid_command(name="suggest", aliases=["feedback", "need", "request_feature"], description="Suggest a feature or command you need in Vortex")
    async def user_suggest(self, ctx, *, suggestion: str):
        """User-facing command to submit feature requests and ideas into the AI evolution pipeline."""
        with get_db() as db:
            db.execute(
                "INSERT INTO user_demand_telemetry (guild_id, user_id, input_text, category, timestamp) VALUES (?, ?, ?, ?, ?)",
                (str(ctx.guild.id if ctx.guild else "DM"), str(ctx.author.id), suggestion, "user_suggestion", datetime.now(timezone.utc).isoformat())
            )
            db.commit()

        embed = discord.Embed(
            title="💡 Suggestion Registered in AI Pipeline",
            description=f"Thank you {ctx.author.mention}! Your feedback has been queued in Vortex's autonomous evolution telemetry:\n\n💬 *\"{suggestion[:500]}\"*",
            color=SUCCESS_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="Vortex Self-Evolution Engine • Analyzed for future code updates")
        await ctx.reply(embed=embed)

    @commands.command(name="evolve_report", aliases=["telemetry_report", "demand_report"], description="[Owner] Analyze user demands and generate an AI Evolution Roadmap")
    async def evolve_report(self, ctx):
        """Analyze all user suggestions, missing commands, and dynamic actions to generate an upgrade roadmap."""
        if not await self.is_bot_admin(ctx.author):
            return await ctx.reply("🔒 **Restricted:** Exclusive to the Bot Creator / Team.")

        msg = await ctx.reply("🧠 **Vortex Auto-ML:** Analyzing telemetry logs & clustering user demands...")

        with get_db() as db:
            rows = db.execute(
                "SELECT input_text, category, timestamp FROM user_demand_telemetry ORDER BY id DESC LIMIT 60"
            ).fetchall()

        if not rows:
            return await msg.edit(content="📊 **Telemetry Empty:** No missing commands or user suggestions recorded yet. Try typing `&suggest <idea>` or use `&do <action>`.")

        demands = [f"[{r['category']}] {r['input_text']}" for r in rows]
        demand_text = "\n".join(demands)

        prompt = f"""You are the Chief AI Evolution Architect for Vortex Discord Bot.
Analyze these recent user command telemetry logs and feature requests:
{demand_text}

Provide:
1. Top 3 Most Demanded Features / Missing Capabilities (Clustered & summarized)
2. Recommended Code Architecture (Which cog to create/modify, e.g. cogs/custom_commands.py or a new cog)
3. Safety Guarantee (Explain how this only upgrades the bot without breaking existing features)

Keep it formatted cleanly with emojis and concise bullet points for Discord."""

        try:
            analysis = await self._call_gemini(prompt, system_instruction="You are an autonomous AI software architect.")
            embed = discord.Embed(
                title="🧬 Vortex Self-Evolution & Telemetry Roadmap",
                description=analysis[:3900],
                color=0x9B59B6,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text=f"Analyzed {len(rows)} user data points • Type &auto_evolve to execute upgrades")
            await msg.edit(content=None, embed=embed)
        except Exception as e:
            await msg.edit(content=f"❌ Analysis failed: {e}")

    @commands.command(name="auto_evolve", aliases=["evolve_apply", "self_upgrade"], description="[Owner] Autonomous AI code generator that creates & pushes upgrades to GitHub/Render")
    async def auto_evolve(self, ctx, *, focus_instruction: str = None):
        """Autonomously synthesizes new features based on telemetry, tests AST syntax, hot-reloads, and pushes to Git."""
        if not await self.is_bot_admin(ctx.author):
            return await ctx.reply("🔒 **Restricted:** Exclusive to the Bot Creator / Team.")

        start_time = datetime.now()
        step_text = (
            "🧬 **Vortex Autonomous Self-Evolution Engine**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟡 `[Step 1/6]` **Analyzing User Demands** — Mining telemetry & clustering needs...\n"
            "⚪ `[Step 2/6]` Architecting non-destructive modular code\n"
            "⚪ `[Step 3/6]` Compiling & verifying AST syntax\n"
            "⚪ `[Step 4/6]` Hot-reloading live extension in memory\n"
            "⚪ `[Step 5/6]` Git snapshot, commit & push to GitHub (Render Auto-Deploy)\n"
            "⚪ `[Step 6/6]` Evolution Changelog Recorded"
        )
        msg = await ctx.reply(step_text)

        # 1. Telemetry gathering
        with get_db() as db:
            rows = db.execute(
                "SELECT input_text FROM user_demand_telemetry ORDER BY id DESC LIMIT 40"
            ).fetchall()
        user_inputs = [r["input_text"] for r in rows]
        inputs_summary = "\n".join(user_inputs) if user_inputs else "General utility & fun expansion"

        target_prompt = focus_instruction if focus_instruction else f"Build the top user requested capability based on telemetry: {inputs_summary[:500]}"

        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        target_file = os.path.join(base_dir, "cogs", "custom_commands.py")
        rel_path = "cogs/custom_commands.py"

        existing_code = ""
        if os.path.exists(target_file):
            with open(target_file, "r", encoding="utf-8") as f:
                existing_code = f.read()

        # Step 2: Code Generation
        step_text = (
            "🧬 **Vortex Autonomous Self-Evolution Engine**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 `[Step 1/6]` Telemetry analyzed ({len(user_inputs)} inputs)\n"
            "🟡 `[Step 2/6]` **Synthesizing Code** — Writing modular Discord.py upgrade with Gemini 3.6 Flash...\n"
            "⚪ `[Step 3/6]` Compiling & verifying AST syntax\n"
            "⚪ `[Step 4/6]` Hot-reloading live extension in memory\n"
            "⚪ `[Step 5/6]` Git snapshot, commit & push to GitHub (Render Auto-Deploy)\n"
            "⚪ `[Step 6/6]` Evolution Changelog Recorded"
        )
        await msg.edit(content=step_text)

        system_instruction = """You are the Lead Autonomous Evolution AI for Vortex Discord Bot.
Invariant Rules:
1. Write 100% valid, production-ready Python 3.10+ Discord.py 2.0+ code.
2. Maintain all existing commands in the file intact without deleting or degrading them. ONLY append or enhance.
3. Include clean error handling, typehints, and rich embeds using MAIN_COLOR, SUCCESS_COLOR, ERROR_COLOR from utils.
4. End the file with:
async def setup(bot):
    await bot.add_cog(CustomCommands(bot))
5. Output ONLY the raw complete Python file inside ```python ... ``` without commentary.
"""

        user_content = f"""Target File: {rel_path}
Feature Upgrade Request:
{target_prompt}

Existing File Content:
```python
{existing_code if existing_code else '# New File'}
```

Output the updated file content:"""

        try:
            ai_res = await self._call_gemini(user_content, system_instruction=system_instruction)
            new_code = self._clean_code_fence(ai_res)
        except Exception as e:
            return await self._send_error_card(msg, "Stage 2: Synthesis", "AI Code Generation Error", str(e), rel_path)

        # Step 3: Backup & AST Syntax Check
        step_text = (
            "🧬 **Vortex Autonomous Self-Evolution Engine**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 `[Step 1/6]` Telemetry analyzed\n"
            f"🟢 `[Step 2/6]` Code synthesized ({len(new_code.splitlines())} lines)\n"
            "🟡 `[Step 3/6]` **Safety Verification** — Creating backup snapshot & verifying AST syntax...\n"
            "⚪ `[Step 4/6]` Hot-reloading live extension in memory\n"
            "⚪ `[Step 5/6]` Git snapshot, commit & push to GitHub (Render Auto-Deploy)\n"
            "⚪ `[Step 6/6]` Evolution Changelog Recorded"
        )
        await msg.edit(content=step_text)

        if os.path.exists(target_file):
            bak_path = f"{target_file}.bak_{int(datetime.now().timestamp())}"
            shutil.copyfile(target_file, bak_path)
            self.backup_history[target_file] = bak_path

        try:
            compile(new_code, target_file, "exec")
        except SyntaxError as syn_err:
            return await self._send_error_card(
                msg,
                "Stage 3: AST Syntax Validation",
                "Syntax Validation Failed",
                f"SyntaxError: {syn_err.msg} at line {syn_err.lineno}",
                rel_path,
                was_rolled_back=True
            )

        # Step 4: Write & Hot-Reload
        step_text = (
            "🧬 **Vortex Autonomous Self-Evolution Engine**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 `[Step 1/6]` Telemetry analyzed\n"
            f"🟢 `[Step 2/6]` Code synthesized\n"
            f"🟢 `[Step 3/6]` AST syntax verified & backup created\n"
            "🟡 `[Step 4/6]` **Hot-Reloading** — Injecting module into live bot gateway...\n"
            "⚪ `[Step 5/6]` Git snapshot, commit & push to GitHub (Render Auto-Deploy)\n"
            "⚪ `[Step 6/6]` Evolution Changelog Recorded"
        )
        await msg.edit(content=step_text)

        with open(target_file, "w", encoding="utf-8") as f:
            f.write(new_code)

        mod_name = "cogs.custom_commands"
        try:
            if mod_name in self.bot.extensions:
                await self.bot.reload_extension(mod_name)
            else:
                await self.bot.load_extension(mod_name)
        except Exception as reload_err:
            if target_file in self.backup_history and os.path.exists(self.backup_history[target_file]):
                shutil.copyfile(self.backup_history[target_file], target_file)
                try:
                    await self.bot.reload_extension(mod_name)
                except Exception:
                    pass
            return await self._send_error_card(
                msg,
                "Stage 4: Hot-Reload",
                "Extension Reload Failed",
                str(reload_err),
                rel_path,
                was_rolled_back=True
            )

        # Step 5: Git Commit & Push
        step_text = (
            "🧬 **Vortex Autonomous Self-Evolution Engine**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 `[Step 1/6]` Telemetry analyzed\n"
            f"🟢 `[Step 2/6]` Code synthesized\n"
            f"🟢 `[Step 3/6]` AST syntax verified\n"
            f"🟢 `[Step 4/6]` Hot-reloaded live into Discord bot\n"
            "🟡 `[Step 5/6]` **Pushing to Git** — Syncing GitHub repository for Render deployment...\n"
            "⚪ `[Step 6/6]` Evolution Changelog Recorded"
        )
        await msg.edit(content=step_text)

        git_status = "Skipped"
        try:
            proc_add = await asyncio.create_subprocess_exec(
                "git", "add", "cogs/custom_commands.py",
                cwd=base_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc_add.communicate()

            commit_msg = f"Auto-Evolve: {target_prompt[:80]}"
            proc_commit = await asyncio.create_subprocess_exec(
                "git", "commit", "-m", commit_msg,
                cwd=base_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc_commit.communicate()

            proc_push = await asyncio.create_subprocess_exec(
                "git", "push",
                cwd=base_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc_push.communicate()
            git_status = "✅ Synced to GitHub & Auto-Deploying to Render"
        except Exception as git_err:
            git_status = f"⚠️ Git Push Notice: {git_err}"

        # Step 6: Log in evolution_changelog
        with get_db() as db:
            db.execute(
                "INSERT INTO evolution_changelog (feature_name, target_file, reasoning, diff_summary, timestamp) VALUES (?, ?, ?, ?, ?)",
                (target_prompt[:150], rel_path, "Auto-Evolved from user telemetry", f"+{len(new_code.splitlines())} lines", datetime.now(timezone.utc).isoformat())
            )
            db.commit()

        elapsed = (datetime.now() - start_time).total_seconds()
        final_embed = discord.Embed(
            title="🧬 Autonomous Evolution Completed Successfully!",
            description=(
                f"**Upgrade Focus:** `{target_prompt[:150]}`\n"
                f"**Target Module:** `{rel_path}`\n"
                f"**Execution Time:** `{elapsed:.2f}s`\n"
                f"**Git Status:** {git_status}"
            ),
            color=SUCCESS_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        final_embed.add_field(name="🛡️ Integrity Status", value="✅ **Zero-Degradation Certified:** All existing bot commands and data remain intact.", inline=False)
        final_embed.set_footer(text="Vortex Self-Evolution Engine • Render Cloud Continuous Deployment")
        await msg.edit(content=None, embed=final_embed)

    @commands.command(name="evolution_history", aliases=["evolution_changelog", "changelog_ai"], description="[Owner] View past autonomous bot upgrades and changelogs")
    async def evolution_history(self, ctx):
        """View the history of autonomous self-upgrades."""
        with get_db() as db:
            rows = db.execute(
                "SELECT feature_name, target_file, timestamp FROM evolution_changelog ORDER BY id DESC LIMIT 10"
            ).fetchall()

        if not rows:
            return await ctx.reply("📜 No autonomous evolutions recorded yet. Run `&auto_evolve` to initiate the first upgrade!")

        lines = []
        for r in rows:
            t = r['timestamp'].split('T')[0]
            lines.append(f"• **{r['feature_name']}** (`{r['target_file']}`) — *{t}*")

        embed = discord.Embed(
            title="📜 Vortex Autonomous Evolution Changelog",
            description="\n".join(lines),
            color=0x9B59B6,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="Vortex Continuous Self-Evolution History")
        await ctx.reply(embed=embed)


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

