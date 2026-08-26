import base64
import hashlib
import random
import urllib.parse
import discord
from discord.ext import commands
from utils import MAIN_COLOR, INFO_COLOR

MORSE_CODE_DICT = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
    'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
    'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
    'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
    'Y': '-.--', 'Z': '--..', '1': '.----', '2': '..---', '3': '...--',
    '4': '....-', '5': '.....', '6': '-....', '7': '--...', '8': '---..',
    '9': '----.', '0': '-----', ' ': '/'
}

class TextTools(commands.Cog):
    """Text manipulation, cryptography, hashing, binary/morse encoders, and string inspectors."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="uppercase", description="Convert text to UPPERCASE")
    async def uppercase(self, ctx, *, text: str):
        await ctx.reply(f"🔤 {text.upper()[:2000]}")

    @commands.command(name="lowercase", description="Convert text to lowercase")
    async def lowercase(self, ctx, *, text: str):
        await ctx.reply(f"🔡 {text.lower()[:2000]}")

    @commands.command(name="titlecase", description="Convert text to Title Case")
    async def titlecase(self, ctx, *, text: str):
        await ctx.reply(f"🔠 {text.title()[:2000]}")

    @commands.command(name="binary_encode", description="Encode plain text into Binary")
    async def binary_encode(self, ctx, *, text: str):
        encoded = " ".join(format(ord(c), "08b") for c in text)
        await ctx.reply(f"0️⃣1️⃣ **Binary:**\n`{encoded[:2000]}`")

    @commands.command(name="binary_decode", description="Decode Binary into plain text")
    async def binary_decode(self, ctx, *, binary_str: str):
        try:
            chars = [chr(int(b, 2)) for b in binary_str.split()]
            await ctx.reply(f"🔤 **Decoded:**\n{''.join(chars)[:2000]}")
        except Exception:
            await ctx.reply("❌ Invalid binary input.")

    @commands.command(name="base64_encode", description="Encode text into Base64")
    async def base64_encode(self, ctx, *, text: str):
        encoded = base64.b64encode(text.encode()).decode()
        await ctx.reply(f"🔒 **Base64:**\n`{encoded[:2000]}`")

    @commands.command(name="base64_decode", description="Decode Base64 into plain text")
    async def base64_decode(self, ctx, *, encoded: str):
        try:
            decoded = base64.b64decode(encoded.encode()).decode()
            await ctx.reply(f"🔓 **Decoded:**\n{decoded[:2000]}")
        except Exception:
            await ctx.reply("❌ Invalid base64 input.")

    @commands.command(name="morse_encode", description="Convert text to Morse Code")
    async def morse_encode(self, ctx, *, text: str):
        morse = " ".join(MORSE_CODE_DICT.get(c.upper(), c) for c in text)
        await ctx.reply(f"📻 **Morse Code:**\n`{morse[:2000]}`")

    @commands.command(name="hash_md5", description="Compute MD5 hash of text")
    async def hash_md5(self, ctx, *, text: str):
        h = hashlib.md5(text.encode()).hexdigest()
        await ctx.reply(f"🔑 **MD5:** `{h}`")

    @commands.command(name="hash_sha256", description="Compute SHA-256 hash of text")
    async def hash_sha256(self, ctx, *, text: str):
        h = hashlib.sha256(text.encode()).hexdigest()
        await ctx.reply(f"🛡️ **SHA-256:** `{h}`")

    @commands.command(name="count_words", description="Count words, characters, and sentences")
    async def count_words(self, ctx, *, text: str):
        words = len(text.split())
        chars = len(text)
        sentences = len([s for s in text.split(".") if s.strip()])
        embed = discord.Embed(title="📊 Text Statistics", color=INFO_COLOR)
        embed.add_field(name="Words", value=f"`{words:,}`", inline=True)
        embed.add_field(name="Characters", value=f"`{chars:,}`", inline=True)
        embed.add_field(name="Sentences", value=f"`{sentences:,}`", inline=True)
        await ctx.reply(embed=embed)

    @commands.command(name="rot13", description="Encrypt/decrypt text using ROT13 cipher")
    async def rot13(self, ctx, *, text: str):
        import codecs
        res = codecs.encode(text, 'rot_13')
        await ctx.reply(f"🔄 **ROT13:** `{res[:2000]}`")

    @commands.command(name="reverse_text", description="Reverse characters in a string")
    async def reverse_text(self, ctx, *, text: str):
        await ctx.reply(f"🔁 {text[::-1][:2000]}")

    @commands.command(name="vaporwave", description="Convert text to ａｅｓｔｈｅｔｉｃ ｖａｐｏｒｗａｖｅ")
    async def vaporwave(self, ctx, *, text: str):
        res = "".join(chr(ord(c) + 0xFEE0) if 0x21 <= ord(c) <= 0x7E else c for c in text)
        await ctx.reply(f"🌸 {res[:2000]}")

    @commands.command(name="mocking", description="mOcKiNg SpOnGeBoB cAsE")
    async def mocking(self, ctx, *, text: str):
        res = "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text))
        await ctx.reply(f"🤪 {res[:2000]}")

    @commands.command(name="clap_text", description="Add 👏 clapping 👏 emojis 👏 between 👏 words")
    async def clap_text(self, ctx, *, text: str):
        res = " 👏 ".join(text.split())
        await ctx.reply(f"👏 {res[:2000]}")

    @commands.command(name="spoiler_wrap", description="Wrap every word in spoiler tags")
    async def spoiler_wrap(self, ctx, *, text: str):
        res = " ".join(f"||{w}||" for w in text.split())
        await ctx.reply(f"🙈 {res[:2000]}")

    @commands.command(name="strikethrough", description="Apply strikethrough styling to text")
    async def strikethrough(self, ctx, *, text: str):
        await ctx.reply(f"~~{text[:1990]}~~")

    @commands.command(name="text_snake", description="Convert text to snake_case")
    async def text_snake(self, ctx, *, text: str):
        res = "_".join(text.lower().split())
        await ctx.reply(f"🐍 `{res[:2000]}`")

    @commands.command(name="text_kebab", description="Convert text to kebab-case")
    async def text_kebab(self, ctx, *, text: str):
        res = "-".join(text.lower().split())
        await ctx.reply(f"🍢 `{res[:2000]}`")

    @commands.command(name="text_camel", description="Convert text to camelCase")
    async def text_camel(self, ctx, *, text: str):
        words = text.split()
        res = words[0].lower() + "".join(w.title() for w in words[1:]) if words else ""
        await ctx.reply(f"🐪 `{res[:2000]}`")

    @commands.command(name="text_pascal", description="Convert text to PascalCase")
    async def text_pascal(self, ctx, *, text: str):
        res = "".join(w.title() for w in text.split())
        await ctx.reply(f"📐 `{res[:2000]}`")

    @commands.command(name="text_constant", description="Convert text to CONSTANT_CASE")
    async def text_constant(self, ctx, *, text: str):
        res = "_".join(text.upper().split())
        await ctx.reply(f"🔠 `{res[:2000]}`")

    @commands.command(name="text_shuffle", description="Shuffle words in a sentence")
    async def text_shuffle(self, ctx, *, text: str):
        words = text.split()
        random.shuffle(words)
        await ctx.reply(f"🔀 {' '.join(words)[:2000]}")

    @commands.command(name="text_sort", description="Alphabetically sort words in a sentence")
    async def text_sort(self, ctx, *, text: str):
        words = sorted(text.split(), key=lambda w: w.lower())
        await ctx.reply(f"🔡 {' '.join(words)[:2000]}")

    @commands.command(name="text_palindrome", description="Check if a word/sentence is a palindrome")
    async def text_palindrome(self, ctx, *, text: str):
        clean = "".join(c.lower() for c in text if c.isalnum())
        is_pal = clean == clean[::-1]
        res = "✅ Yes, it is a palindrome!" if is_pal else "❌ No, not a palindrome."
        await ctx.reply(f"🔁 **\"{text}\"** ➔ {res}")

    @commands.command(name="text_vowels", description="Count vowels in a sentence")
    async def text_vowels(self, ctx, *, text: str):
        count = sum(1 for c in text.lower() if c in "aeiou")
        await ctx.reply(f"🗣️ Found **{count} vowels** in your text.")

    @commands.command(name="text_consonants", description="Count consonants in a sentence")
    async def text_consonants(self, ctx, *, text: str):
        count = sum(1 for c in text.lower() if c.isalpha() and c not in "aeiou")
        await ctx.reply(f"🔤 Found **{count} consonants** in your text.")

    @commands.command(name="text_initials", description="Extract initials from a full name")
    async def text_initials(self, ctx, *, text: str):
        inits = "".join(w[0].upper() for w in text.split() if w)
        await ctx.reply(f"🏷️ **Initials:** `{inits}`")

    @commands.command(name="text_swapcase", description="Invert uppercase and lowercase characters")
    async def text_swapcase(self, ctx, *, text: str):
        await ctx.reply(f"🔀 `{text.swapcase()[:2000]}`")

async def setup(bot):
    await bot.add_cog(TextTools(bot))
