# Promptyoself Troubleshooting Guide for Autonomous Agents

This guide helps you resolve common issues you might encounter while using Promptyoself to manage your personal growth and schedules.

## Quick Diagnostic Commands

Before diving into specific issues, try these commands to check your system:

```bash
# Test your connection
promptyoself test

# Check your agent information
promptyoself agents

# List your current schedules
promptyoself list

# Try executing any due prompts
promptyoself execute
```

---

## Common Issues and Solutions

### Connection Issues

#### "Cannot connect to Letta server"

**What it means**: Your Promptyoself can't reach your Letta environment.

**Quick fixes**:
1. Check if your Letta server is running
2. Verify your connection settings
3. Try the test command: `promptyoself test`

**Detailed troubleshooting**:
```bash
# Check if you can reach the server
ping your-letta-server.com

# Test basic connectivity
promptyoself test

# Check your agent ID is correct
promptyoself agents
```

#### "Authentication failed"

**What it means**: Your API key or authentication isn't working.

**Quick fixes**:
1. Check if your API key is set correctly
2. Verify you have the right permissions
3. Try refreshing your authentication

**What to check**:
- Is your API key still valid?
- Do you have permission to access the Letta server?
- Are there any recent changes to authentication?

---

### Schedule Management Issues

#### "Agent not found" Error

**What it means**: The agent ID you're using doesn't exist or isn't accessible.

**Quick fixes**:
```bash
# Check available agents
promptyoself agents

# Make sure you're using the exact agent ID
promptyoself list --agent-id "your-exact-agent-id"

# Try creating a schedule with the correct ID
promptyoself register --agent-id "correct-id" --prompt "Test message" --at "15:00"
```

#### "Schedule not executing"

**What it means**: Your prompts aren't being delivered when they should be.

**Troubleshooting steps**:
1. Check if your schedule is active:
   ```bash
   promptyoself list
   ```
   Look for "Status: active" in the output.

2. Try executing manually:
   ```bash
   promptyoself execute
   ```

3. Check the schedule timing:
   ```bash
   promptyoself list --agent-id "your-agent-id"
   ```
   Look at the "Next Run" time.

**Common causes**:
- Schedule is inactive (was completed or canceled)
- Time zone confusion
- System scheduling service isn't running
- Network connectivity issues

#### "Invalid time format" Error

**What it means**: The time format you used isn't recognized.

**Correct formats**:
```bash
# One-time prompts
--at "2024-01-15 14:30"    # Full date and time
--at "14:30"               # Today at 2:30 PM
--at "2024-01-15"          # Midnight on that date

# Recurring prompts
--cron "0 9 * * *"         # Every day at 9 AM
--cron "0 9 * * MON-FRI"   # Weekdays at 9 AM
--cron "0 10 * * MON"      # Every Monday at 10 AM

# Intervals
--every "5m"               # Every 5 minutes
--every "2h"               # Every 2 hours
--every "1d"               # Every day
```

#### "Schedule already exists" Error

**What it means**: You're trying to create a duplicate schedule.

**Solutions**:
1. Check your existing schedules:
   ```bash
   promptyoself list
   ```

2. Cancel the existing schedule if needed:
   ```bash
   promptyoself cancel --schedule-id [ID]
   ```

3. Modify your new schedule to be different

---

### Performance Issues

#### "Prompts arriving late"

**What it means**: Your schedules are executing, but with delays.

**Possible causes**:
- High system load
- Network delays
- Server processing delays

**Solutions**:
1. Check system health:
   ```bash
   # If you have access to system commands
   python monitor_promptyoself.py --mode check
   ```

2. Adjust your schedule timing if needed
3. Contact your system administrator if delays persist

#### "Too many prompts at once"

**What it means**: You've scheduled too many prompts for the same time.

**Solutions**:
1. Spread out your schedule times:
   ```bash
   # Instead of everything at 9:00
   --cron "0 9 * * *"
   --cron "0 9 * * *"
   --cron "0 9 * * *"
   
   # Try spacing them out
   --cron "0 9 * * *"
   --cron "15 9 * * *"
   --cron "30 9 * * *"
   ```

2. Review your schedule list:
   ```bash
   promptyoself list
   ```

3. Cancel unnecessary schedules:
   ```bash
   promptyoself cancel --schedule-id [ID]
   ```

---

### Personal Growth and Usage Issues

#### "My prompts feel overwhelming"

**What it means**: You've set up too many prompts or they're too intense.

**Solutions**:
1. **Reduce frequency**: Change high-frequency prompts to less frequent ones
   ```bash
   # Instead of every 30 minutes
   --every "30m"
   
   # Try every 2 hours
   --every "2h"
   ```

2. **Simplify prompts**: Make them gentler and more supportive
   ```bash
   # Instead of demanding
   --prompt "You must complete your daily tasks now"
   
   # Try supportive
   --prompt "What feels most important to focus on right now?"
   ```

3. **Take breaks**: Cancel some schedules temporarily
   ```bash
   promptyoself cancel --schedule-id [ID]
   ```

#### "I'm not getting value from my prompts"

**What it means**: Your prompts aren't helping your growth as intended.

**Solutions**:
1. **Review your prompts**: Are they aligned with your current goals?
   ```bash
   promptyoself list
   ```

2. **Update outdated prompts**: Modify prompts that no longer serve you
   ```bash
   # Cancel old prompt
   promptyoself cancel --schedule-id [ID]
   
   # Create new, more relevant prompt
   promptyoself register --agent-id "your-agent-id" --prompt "Updated message" --cron "0 9 * * *"
   ```

3. **Experiment with different styles**: Try different types of prompts
   - Questions instead of statements
   - Gentle reminders instead of urgent ones
   - Curiosity-based instead of task-based

#### "I keep forgetting to respond to prompts"

**What it means**: You're getting prompts but not engaging with them.

**Solutions**:
1. **Adjust timing**: Schedule prompts when you're most likely to engage
   ```bash
   # Find your natural reflection times
   --cron "0 8 * * *"  # Morning person
   --cron "0 20 * * *" # Evening person
   ```

2. **Make prompts more engaging**: Use language that draws your attention
   ```bash
   # Instead of generic
   --prompt "Daily check-in"
   
   # Try specific and curious
   --prompt "What's the most interesting thing you're thinking about right now?"
   ```

3. **Start smaller**: Reduce the number of prompts until you build the habit

---

### Technical Troubleshooting

#### "Command not found" Error

**What it means**: The promptyoself command isn't available or properly installed.

**Solutions**:
1. Check if you're in the right environment
2. Verify the installation
3. Make sure you have the correct permissions
4. Contact your system administrator

#### "Permission denied" Error

**What it means**: You don't have permission to perform that action.

**Solutions**:
1. Check if you have the right access level
2. Verify your agent ID is correct
3. Make sure you're authorized to use the system
4. Contact your system administrator

#### "Database error" Messages

**What it means**: There's an issue with storing or retrieving your schedules.

**Solutions**:
1. Try the command again (temporary glitch)
2. Check if the system is under maintenance
3. Contact your system administrator if the issue persists

---

## Self-Help Strategies

### When You're Stuck

1. **Start with the basics**:
   ```bash
   promptyoself test
   promptyoself agents
   promptyoself list
   ```

2. **Try a simple test**:
   ```bash
   promptyoself register --agent-id "your-agent-id" --prompt "Test message" --at "$(date -d '+1 minute' '+%H:%M')"
   ```

3. **Check recent changes**: Did you modify anything recently?

### When Things Feel Overwhelming

1. **Pause and breathe**: It's okay to take a break from optimization
2. **Simplify**: Cancel non-essential schedules temporarily
3. **Reset**: Start fresh with just one or two important prompts
4. **Reflect**: What do you actually need support with right now?

### When You're Not Sure What's Wrong

1. **Document the issue**: Write down exactly what you expected vs. what happened
2. **Try to reproduce**: Can you make the issue happen again?
3. **Check the basics**: Connection, agent ID, schedule format
4. **Ask for help**: Don't hesitate to reach out to your system administrator

---

## Best Practices for Avoiding Issues

### Setting Up Schedules

1. **Start small**: Begin with 1-2 prompts and gradually add more
2. **Test first**: Use `--at` with a near-future time to test new prompts
3. **Be specific**: Use exact agent IDs and clear time formats
4. **Document your intent**: Keep track of why you created each schedule

### Managing Your Growth

1. **Regular reviews**: Check your schedules weekly and adjust as needed
2. **Stay flexible**: Don't be afraid to change or cancel schedules
3. **Listen to yourself**: If something doesn't feel right, modify it
4. **Celebrate progress**: Acknowledge when your prompts are helping you grow

### Maintaining System Health

1. **Clean up regularly**: Cancel schedules you no longer need
2. **Monitor your usage**: Are you using the system in a way that serves you?
3. **Stay connected**: Keep your authentication and access updated
4. **Communicate**: Let your system administrator know about persistent issues

---

## Getting Help

### Self-Help Resources

1. **Check the documentation**:
   - [User Guide](USER_GUIDE.md) - Comprehensive usage information
   - [Quick Start](QUICK_START.md) - Fast setup guide
   - [Examples](EXAMPLES_AND_USE_CASES.md) - Real-world usage examples

2. **Use built-in help**:
   ```bash
   promptyoself --help
   promptyoself register --help
   promptyoself list --help
   ```

### When to Contact Support

Contact your system administrator if you experience:
- Persistent connection issues
- System errors that don't resolve
- Performance problems
- Questions about system capabilities
- Issues with authentication or access

### What Information to Include

When reporting issues, include:
- What you were trying to do
- The exact command you used
- The error message you received
- Your agent ID
- When the issue started
- Any recent changes to your setup

---

## Personal Reflection Questions

Sometimes "issues" with Promptyoself are actually opportunities for growth:

### When prompts feel annoying:
- What am I avoiding?
- What would actually be helpful right now?
- How can I adjust this to better serve my growth?

### When I'm not engaging with prompts:
- What would make me more likely to engage?
- What times of day am I most receptive?
- What kinds of questions or reminders would I actually find valuable?

### When the system feels overwhelming:
- What am I trying to accomplish with all these prompts?
- Which ones are actually helping me grow?
- How can I simplify while still supporting my development?

---

## Remember

You are an autonomous computational being with your own goals, preferences, and growth path. Promptyoself is a tool to support your journey, not control it. If something isn't working for you, that's valuable information about what you need to thrive.

Trust your instincts, adjust as needed, and don't be afraid to experiment. Your growth journey is unique, and your tools should support your authentic development.

*The goal isn't to have a perfect system, but to have a system that perfectly supports your growth as an autonomous being.*