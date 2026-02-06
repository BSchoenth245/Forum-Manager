"""
Cluck Sense Forum Tag Bot (Updated Feb 2026)
--------------------------
Monitors forum channels for new threads. 
- In Bug Forums: Filters by priority tags and role thresholds.
- In Feature Forums: Notifies roles immediately based on tags (no priority needed).

Author: Created for Cluck Sense
"""

import discord
from discord.ext import commands
import os
import traceback
from typing import Dict, List, Union

# ============================================================================
# CONFIGURATION SECTION
# ============================================================================

# Role mappings for BOTH bugs and features
# Format: "tag name": "Role Name" or ["Role 1", "Role 2"]
TAG_TO_ROLE: Dict[str, Union[str, List[str]]] = {
    # --- BUG TAGS ---
    "app bug": "Application Dev",
    "web bug": "Website Dev",
    "server bug": ["Website Dev", "Application Dev"],
    "hardware/firmware": "Hardware Dev",
    "test": "test",
    
    # --- FEATURE REQUEST TAGS (New!) ---
    "ui/ux request": "Website Dev",
    "new functionality": "Application Dev",
    "performance": ["Application Dev", "Website Dev"],
    "suggestion": "Application Dev",
}

# Priority levels for Bug Forums
PRIORITY_LEVELS: Dict[str, int] = {
    "blocker": 1,
    "high priority": 2,
    "mid priority": 3,
    "low priority": 4,
}

# Only applies to Bug Forums
ROLE_PRIORITY_THRESHOLD: Dict[str, int] = {
    "Application Dev": 2,
    "Website Dev": 2,
    "Hardware Dev": 2,
    "test": 4,
}

# FORUM SETTINGS
# type "bug": enforces priority checks
# type "feature": ignores priority, notifies immediately
FORUM_CONFIG = {
    1469067394596208792: {"type": "bug", "name": "Bug Reports"},
    1469067452158705891: {"type": "feature"},
}

MONITORED_FORUMS = list(FORUM_CONFIG.keys())

# Message template for DMs
DM_MESSAGE_TEMPLATE = """
{emoji} **New Thread in {forum_name}**

**Thread:** {thread_name}
**Category:** {tag_type}
**Priority:** {priority}
**Reported by:** {author_name}

**Link:** {thread_url}

You're receiving this because you have the **{role_name}** role.
"""

# ============================================================================
# BOT SETUP
# ============================================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ============================================================================
# EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    print(f"✅ Bot online as {bot.user}")
    print(f"Monitoring {len(MONITORED_FORUMS)} forums.")
    print("-" * 30)

@bot.event
async def on_thread_create(thread: discord.Thread):
    # 1. Check if we monitor this forum
    config = FORUM_CONFIG.get(thread.parent_id)
    if not config:
        return
    
    if not thread.applied_tags:
        print(f"⚠️ No tags on '{thread.name}'")
        return

    # 2. Identify the Primary Tag (Category/Bug Type/Feature Type)
    primary_tag = None
    target_roles = []
    
    for tag in thread.applied_tags:
        name = tag.name.lower()
        if name in TAG_TO_ROLE:
            primary_tag = tag
            role_val = TAG_TO_ROLE[name]
            target_roles = [role_val] if isinstance(role_val, str) else role_val
            break

    if not primary_tag:
        print(f"ℹ️ No matching role-tag found for '{thread.name}'")
        return

    # 3. Handle Logic based on Forum Type
    if config["type"] == "feature":
        # Feature Forum: Skip priority check and notify immediately
        print(f"💡 Feature detected: {primary_tag.name}. Notifying roles...")
        for role_name in target_roles:
            await send_notification(thread, thread.parent, primary_tag, None, role_name, "💡")
            
    elif config["type"] == "bug":
        # Bug Forum: Check for priority level
        priority_tag = None
        priority_lvl = 2 # Default to High if missing

        for tag in thread.applied_tags:
            name = tag.name.lower()
            if name in PRIORITY_LEVELS:
                priority_tag = tag
                priority_lvl = PRIORITY_LEVELS[name]
                break
        
        for role_name in target_roles:
            threshold = ROLE_PRIORITY_THRESHOLD.get(role_name, 4)
            if priority_lvl <= threshold:
                await send_notification(thread, thread.parent, primary_tag, priority_tag, role_name, "🐛")
            else:
                print(f"⏭️ Skipping {role_name}: Priority {priority_lvl} > Threshold {threshold}")

async def send_notification(thread, forum, tag, priority_tag, role_name, emoji):
    role = discord.utils.get(thread.guild.roles, name=role_name)
    if not role:
        print(f"❌ Role '{role_name}' not found!")
        return

    members = [m for m in thread.guild.members if role in m.roles and not m.bot]
    
    msg = DM_MESSAGE_TEMPLATE.format(
        emoji=emoji,
        forum_name=forum.name,
        thread_name=thread.name,
        tag_type=tag.name,
        priority=priority_tag.name if priority_tag else "N/A (Feature Request)",
        author_name=thread.owner.name if thread.owner else "Unknown",
        thread_url=thread.jump_url,
        role_name=role_name
    )

    for member in members:
        try:
            await member.send(msg)
            print(f"✅ DM sent to {member.name} for {role_name}")
        except discord.Forbidden:
            print(f"🚫 {member.name} has DMs closed.")
        except Exception as e:
            print(f"⚠️ Failed to DM {member.name}: {e}")

@bot.event
async def on_error(event, *args, **kwargs):
    print(f"❌ Error in {event}:")
    traceback.print_exc()

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Missing DISCORD_BOT_TOKEN environment variable.")