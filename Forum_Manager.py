"""
Cluck Sense Forum Tag Bot
--------------------------
This bot monitors specified forum channels for new threads with specific tags.
When a matching tag is found, it DMs all users with the corresponding role.

Author: Created for Cluck Sense
Date: February 2026
"""

import discord
from discord.ext import commands
import os
from typing import Dict, List, Union

# ============================================================================
# CONFIGURATION SECTION - CUSTOMIZE THIS FOR YOUR SERVER
# ============================================================================

# Bug Type to Role mapping - PRIMARY TRIGGER
# These are the main tags that determine who gets notified
# Can be a single role (string) or multiple roles (list of strings)
from typing import Union, List as ListType
BUG_TYPE_TO_ROLE: Dict[str, Union[str, ListType[str]]] = {
    "app bug": "Application Dev",                    # App bugs → Application Dev only
    "web bug": "Website Dev",                        # Web bugs → Website Dev only
    "server bug": ["Website Dev", "Application Dev"],   # Server bugs → BOTH Website Dev AND Application Dev
    "hardware/firmware": "Hardware Dev",             # Hardware/Firmware → Hardware Dev only
    "test": "test"
}

# Priority levels that modify notifications - SECONDARY TRIGGER
# These determine IF the notification gets sent based on priority
# Format: priority_tag_name: minimum_priority_level
# Lower numbers = higher priority (1 is most urgent, 4 is least urgent)
PRIORITY_LEVELS: Dict[str, int] = {
    "blocker": 1,        # Most urgent - always notify
    "high priority": 2,  # High urgency - notify for most bugs
    "mid priority": 3,   # Medium urgency - may skip for some scenarios
    "low priority": 4,   # Low urgency - may skip for some scenarios
}

# Notification threshold per role (optional - set to 4 to notify for all priorities)
# Only send notification if bug priority <= this threshold
# 1 = only Blocker, 2 = Blocker + High, 3 = Blocker + High + Mid, 4 = all priorities
ROLE_PRIORITY_THRESHOLD: Dict[str, int] = {
    "Application Dev": 2,  # Only notify for Blocker and High Priority
    "Website Dev": 2,      # Only notify for Blocker and High Priority
    "Hardware Dev": 2,     # Only notify for Blocker and High Priority
    "test": 4,             # Test role: notify for everything"
    # Set to 4 if you want to be notified for ALL priorities including Low
}

# Forum channels to monitor (use channel IDs, found by right-clicking channel)
# To get channel IDs: Enable Developer Mode in Discord settings, right-click channel, Copy ID
MONITORED_FORUMS: List[int] = [
    1469067394596208792,
]

# Required tags per forum (optional - leave empty to not enforce)
# Format: channel_id: ["category_keyword_1", "category_keyword_2"]
# The bot will warn if these categories seem to be missing
REQUIRED_TAGS_PER_FORUM: Dict[int, List[str]] = {
    # Example: Bug reports forum requires a bug type tag AND a priority tag
    1469067394596208792: ["priority", "bug"],  # Replace with actual channel ID
}

# Message template for DMs
DM_MESSAGE_TEMPLATE = """
🐛 **New Bug Report in {forum_name}**

**Thread:** {thread_name}
**Bug Type:** {bug_type}
**Priority:** {priority}
**Reported by:** {author_name}

**Link:** {thread_url}

You're receiving this because you have the **{role_name}** role and this is a **{bug_type}** issue.
"""

# ============================================================================
# BOT SETUP
# ============================================================================

# Set up bot with necessary intents
intents = discord.Intents.default()
intents.guilds = True           # Access to guild/server info
intents.members = True          # Access to member info (needed to find users by role)
intents.message_content = True  # Access to message content

# Create bot instance with command prefix (not really used but required)
bot = commands.Bot(command_prefix="!", intents=intents)

# ============================================================================
# EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """
    Triggered when the bot successfully connects to Discord.
    Prints confirmation and bot information.
    """
    print(f"✅ Bot is online and logged in as {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print(f"Monitoring {len(MONITORED_FORUMS)} forum channel(s)")
    print(f"Watching for tags: {list(BUG_TYPE_TO_ROLE.keys())}")
    print("-" * 50)


@bot.event
async def on_thread_create(thread: discord.Thread):
    """
    Triggered when a new thread is created in any channel.
    Logic:
    1. Check if thread is in a monitored forum
    2. Extract bug type tag (determines WHO to notify)
    3. Extract priority tag (determines IF to notify)
    4. Notify appropriate role(s) if priority meets threshold
    
    Args:
        thread: The newly created thread object
    """
    # Check if this thread is in one of our monitored forums
    if thread.parent_id not in MONITORED_FORUMS:
        return  # Not a forum we're monitoring, ignore it
    
    # Get the forum channel object
    forum_channel = thread.parent
    
    # Check if thread has any tags
    if not thread.applied_tags:
        print(f"⚠️  New thread '{thread.name}' has no tags!")
        return
    
    # Get all tag names from the thread (lowercase for matching)
    thread_tag_names = [tag.name.lower() for tag in thread.applied_tags]
    
    print(f"ℹ️  New thread '{thread.name}' with tags: {[tag.name for tag in thread.applied_tags]}")
    
    # Step 1: Find the bug type tag (primary trigger)
    bug_type_tag = None
    target_roles = []
    
    for tag in thread.applied_tags:
        tag_name_lower = tag.name.lower()
        if tag_name_lower in BUG_TYPE_TO_ROLE:
            bug_type_tag = tag
            role_config = BUG_TYPE_TO_ROLE[tag_name_lower]
            
            # Handle both single role (string) and multiple roles (list)
            if isinstance(role_config, str):
                target_roles = [role_config]
            else:
                target_roles = role_config
            
            print(f"🎯 Bug type identified: '{tag.name}' → Roles: {target_roles}")
            break
    
    if not bug_type_tag:
        print(f"⚠️  No recognized bug type tag found. Available: {list(BUG_TYPE_TO_ROLE.keys())}")
        return
    
    # Step 2: Find the priority tag (secondary filter)
    priority_tag = None
    priority_level = None
    
    for tag in thread.applied_tags:
        tag_name_lower = tag.name.lower()
        if tag_name_lower in PRIORITY_LEVELS:
            priority_tag = tag
            priority_level = PRIORITY_LEVELS[tag_name_lower]
            print(f"📊 Priority identified: '{tag.name}' (level {priority_level})")
            break
    
    if not priority_tag:
        print(f"⚠️  No priority tag found. Available: {list(PRIORITY_LEVELS.keys())}")
        print(f"   Defaulting to 'High Priority' for notification purposes")
        priority_level = 2  # Default to high priority if not specified
    
    # Step 3: Notify each target role if priority meets their threshold
    for role_name in target_roles:
        threshold = ROLE_PRIORITY_THRESHOLD.get(role_name, 4)  # Default: notify all priorities
        
        if priority_level > threshold:
            print(f"⏭️  Priority level {priority_level} does not meet threshold {threshold} for '{role_name}'")
            print(f"   Skipping notification for '{role_name}' (too low priority)")
            continue
        
        # Priority meets threshold - send notification
        print(f"✅ Priority level {priority_level} meets threshold {threshold} for '{role_name}'")
        await notify_role_members(thread, forum_channel, bug_type_tag, priority_tag, role_name)


async def notify_role_members(
    thread: discord.Thread, 
    forum_channel: discord.ForumChannel,
    bug_type_tag: discord.ForumTag,
    priority_tag: discord.ForumTag,
    role_name: str
):
    """
    Finds all members with a specific role and sends them a DM about the thread.
    
    Args:
        thread: The thread that was created
        forum_channel: The forum channel containing the thread
        bug_type_tag: The bug type tag that triggered the notification
        priority_tag: The priority tag on the thread (or None)
        role_name: The name of the role to notify
    """
    guild = thread.guild
    
    # Find the role by name
    role = discord.utils.get(guild.roles, name=role_name)
    
    if not role:
        print(f"⚠️  Warning: Role '{role_name}' not found in server!")
        return
    
    # Get all members with this role
    members_to_notify = [member for member in guild.members if role in member.roles]
    
    if not members_to_notify:
        print(f"ℹ️  No members found with role '{role_name}'")
        return
    
    print(f"📨 Sending DMs to {len(members_to_notify)} member(s) with role '{role_name}'")
    
    # Get all tag names for display
    all_tags = ", ".join([t.name for t in thread.applied_tags])
    
    # Prepare the DM message
    message_content = DM_MESSAGE_TEMPLATE.format(
        forum_name=forum_channel.name,
        thread_name=thread.name,
        all_tags=all_tags,
        bug_type=bug_type_tag.name,
        priority=priority_tag.name if priority_tag else "Not specified",
        author_name=thread.owner.name if thread.owner else "Unknown",
        thread_url=thread.jump_url,
        role_name=role_name
    )
    
    # Send DM to each member
    success_count = 0
    fail_count = 0
    
    for member in members_to_notify:
        # Skip bots
        if member.bot:
            continue
            
        try:
            await member.send(message_content)
            success_count += 1
            print(f"   ✅ Sent DM to {member.name}")
        except discord.Forbidden:
            # User has DMs disabled or has blocked the bot
            fail_count += 1
            print(f"   ❌ Could not DM {member.name} (DMs disabled or bot blocked)")
        except Exception as e:
            # Other error occurred
            fail_count += 1
            print(f"   ❌ Error sending DM to {member.name}: {e}")
    
    print(f"📊 Results: {success_count} sent, {fail_count} failed")
    print("-" * 50)


# ============================================================================
# ERROR HANDLING
# ============================================================================

@bot.event
async def on_error(event, *args, **kwargs):
    """
    Global error handler for the bot.
    Prints errors without crashing the bot.
    """
    import traceback
    print(f"❌ Error in {event}:")
    traceback.print_exc()


# ============================================================================
# BOT STARTUP
# ============================================================================

if __name__ == "__main__":
    # Get bot token from environment variable
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    
    if not TOKEN:
        print("❌ ERROR: DISCORD_BOT_TOKEN environment variable not set!")
        print("Please set your bot token before running.")
        exit(1)
    
    # Validate configuration
    if not MONITORED_FORUMS:
        print("⚠️  WARNING: No forums are configured to monitor!")
        print("Please add forum channel IDs to MONITORED_FORUMS list.")
    
    if not BUG_TYPE_TO_ROLE:
        print("⚠️  WARNING: No tag-to-role mappings configured!")
        print("Please add mappings to BUG_TYPE_TO_ROLE dictionary.")
    
    # Start the bot
    print("🚀 Starting Cluck Sense Forum Tag Bot...")
    print("-" * 50)
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ ERROR: Invalid bot token. Please check your DISCORD_BOT_TOKEN.")
    except Exception as e:
        print(f"❌ ERROR: Failed to start bot: {e}")