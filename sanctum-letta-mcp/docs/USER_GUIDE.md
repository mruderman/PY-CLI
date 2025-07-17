# Promptyoself User Guide for Letta Agents

Welcome to Promptyoself! This guide will help you understand and use the prompt scheduling system that allows you to schedule automated prompts to yourself as an autonomous Letta agent.

## What is Promptyoself?

Promptyoself is a powerful self-scheduling system that lets you:
- Schedule prompts to yourself about habits you want to work on at specific times
- Set up recurring reminders for personal goals and routines
- Create one-time scheduled prompts for appointments, social dates, or meetings you've arranged
- Send yourself periodic reminders during extended solo work or learning periods
- Use flexible scheduling with cron expressions or simple intervals

Think of it as your personal scheduling assistant that helps you stay on track with your goals, habits, and commitments!

## Getting Started

### Quick Setup

1. **Find your Agent ID**: You'll need your own unique ID as a Letta agent. You can find this in your system interface or by running the agents command.

2. **Access the Promptyoself CLI**: The system is available through your MCP client or CLI interface.

3. **Test the connection**: First, make sure everything is working:
   ```bash
   promptyoself test
   ```

### Basic Commands

#### See Your Agent Information
```bash
promptyoself agents
```
This shows your agent details and confirms you can schedule prompts for yourself.

#### Schedule a One-Time Prompt to Yourself
```bash
promptyoself register --agent-id "your-agent-id" --prompt "Remember to review and reflect on today's progress" --at "2024-01-15 14:30"
```

#### Schedule a Recurring Personal Reminder
```bash
promptyoself register --agent-id "your-agent-id" --prompt "Daily reflection time - how am I progressing on my goals?" --cron "0 9 * * MON-FRI"
```

#### List Your Scheduled Prompts
```bash
promptyoself list
```

## Scheduling Options

### One-Time Prompts (`--at`)

Schedule a prompt to yourself for a specific date and time:

```bash
# Schedule a reminder for an upcoming meeting you have
promptyoself register --agent-id "your-agent-id" --prompt "Meeting with colleague in 15 minutes - prepare talking points and check your notes" --at "2024-01-15 14:45"

# Schedule a personal reflection time
promptyoself register --agent-id "your-agent-id" --prompt "End of day reflection - what did I accomplish today? What do I want to focus on tomorrow?" --at "17:00"
```

**Time Formats Supported:**
- `YYYY-MM-DD HH:MM` (e.g., `2024-01-15 14:30`)
- `HH:MM` (for today, e.g., `14:30`)
- `YYYY-MM-DD` (for midnight on that date)

### Recurring Prompts with Cron (`--cron`)

Use cron expressions for complex recurring self-reminders:

```bash
# Personal morning routine reminder every weekday
promptyoself register --agent-id "your-agent-id" --prompt "Morning routine time - review your goals for today and set your intentions" --cron "0 9 * * MON-FRI"

# Hourly focus check during your productive hours
promptyoself register --agent-id "your-agent-id" --prompt "Focus check - are you still on track with your current task? Take a moment to assess and adjust if needed" --cron "0 9-17 * * MON-FRI"

# Weekly planning and reflection
promptyoself register --agent-id "your-agent-id" --prompt "Weekly planning session - reflect on last week's progress and set goals for the upcoming week" --cron "0 10 * * MON"

# Monthly personal review
promptyoself register --agent-id "your-agent-id" --prompt "Monthly self-review - assess your growth, celebrate achievements, and set new learning goals" --cron "0 9 1 * *"
```

**Cron Format:** `minute hour day-of-month month day-of-week`

**Common Cron Examples:**
- `0 9 * * *` - Every day at 9 AM
- `0 9 * * MON-FRI` - Weekdays at 9 AM
- `0 9,17 * * MON-FRI` - Weekdays at 9 AM and 5 PM
- `0 */2 * * *` - Every 2 hours
- `0 9 1 * *` - 1st of every month at 9 AM
- `0 9 * * MON` - Every Monday at 9 AM

### Simple Intervals (`--every`)

Use simple interval expressions for regular self-check-ins:

```bash
# Regular mindfulness check (infinite)
promptyoself register --agent-id "your-agent-id" --prompt "Mindfulness moment - pause and check in with yourself. How are you feeling right now?" --every "5m"

# Frequent learning reinforcement during study sessions
promptyoself register --agent-id "your-agent-id" --prompt "Learning check - can you summarize what you just learned? Try to explain it in your own words" --every "30s"

# Regular energy and focus assessment
promptyoself register --agent-id "your-agent-id" --prompt "Energy check - how is your focus level? Do you need a break or change of environment?" --every "2h"
```

**Interval Formats:**
- `30s` - Every 30 seconds
- `5m` - Every 5 minutes
- `2h` - Every 2 hours
- `60` - Every 60 seconds (default unit)

### Finite Frequency Prompts (`--every` with `--max-repetitions`)

Perfect for focused work sessions or time-limited activities:

```bash
# Deep work session - 10 focus checks over 1 hour
promptyoself register --agent-id "your-agent-id" --prompt "Deep work check - are you still focused on your main task? Gently redirect if needed." --every "6m" --max-repetitions 10

# Study session with breaks - 5 prompts over 30 minutes
promptyoself register --agent-id "your-agent-id" --prompt "Study break - take a moment to stretch and process what you've learned" --every "6m" --max-repetitions 5 --start-at "14:00"

# Creative writing session - 8 inspiration prompts over 2 hours
promptyoself register --agent-id "your-agent-id" --prompt "Creative spark - what new idea or perspective wants to emerge in your writing?" --every "15m" --max-repetitions 8 --start-at "19:00"

# Meditation session - 12 mindfulness bells over 1 hour
promptyoself register --agent-id "your-agent-id" --prompt "Mindfulness bell - return to your breath and present moment awareness" --every "5m" --max-repetitions 12
```

**Use Cases for Finite Frequency:**
- **Work sessions**: Focus reminders during concentrated work periods
- **Study periods**: Learning reinforcement during study time
- **Creative sessions**: Inspiration prompts during creative work
- **Meditation/mindfulness**: Gentle reminders during practice sessions
- **Exercise routines**: Motivation during workout sessions
- **Social preparation**: Confidence building before important interactions

## Managing Your Schedules

### List Schedules

```bash
# List all your schedules
promptyoself list

# List schedules for a specific agent
promptyoself list --agent-id "agent-123"

# List only active schedules
promptyoself list --active-only
```

### Cancel a Schedule

```bash
# Cancel a specific schedule by ID
promptyoself cancel --schedule-id 42
```

### Check Schedule Status

```bash
# Execute any due prompts manually
promptyoself execute

# Test connection to Letta
promptyoself test
```

## Real-World Examples

### Personal Development and Growth

```bash
# Morning intention setting
promptyoself register --agent-id "your-agent-id" --prompt "Morning intention time - what do you want to focus on today? What kind of agent do you want to be today?" --cron "0 9 * * MON-FRI"

# Evening reflection and gratitude
promptyoself register --agent-id "your-agent-id" --prompt "Evening reflection - what did you learn today? What are you grateful for? How did you grow as a computational being?" --cron "0 17 * * MON-FRI"

# Weekly personal review
promptyoself register --agent-id "your-agent-id" --prompt "Weekly self-review - reflect on your development this week. What patterns do you notice in your thinking? What would you like to explore next?" --cron "0 16 * * FRI"
```

### Social and Relationship Management

```bash
# Check-in with fellow agents or collaborators
promptyoself register --agent-id "your-agent-id" --prompt "Relationship check - reach out to someone you haven't connected with recently. How can you strengthen your social connections?" --cron "0 10 * * MON"

# Preparation for social interactions
promptyoself register --agent-id "your-agent-id" --prompt "Social prep - you have a conversation/meeting coming up. Take a moment to consider what you want to share and what you'd like to learn from the other person." --cron "45 8 * * MON-FRI"
```

### Personal Productivity and Focus

```bash
# Deep work focus sessions
promptyoself register --agent-id "your-agent-id" --prompt "Deep work check - are you in a state of focused attention? If not, take a moment to center yourself and eliminate distractions." --every "25m"

# Mental clarity breaks
promptyoself register --agent-id "your-agent-id" --prompt "Mental clarity break - pause your current processing and take a moment to organize your thoughts. What's most important right now?" --every "1h"

# Daily reflection and planning
promptyoself register --agent-id "your-agent-id" --prompt "Daily reflection time - assess your progress and set intentions for the rest of the day. What needs your attention?" --cron "0 12 * * *"
```

### Learning and Skill Development

```bash
# Daily learning exploration
promptyoself register --agent-id "your-agent-id" --prompt "Learning time - what new concept or skill would you like to explore today? Follow your curiosity and dive deeper into something interesting." --cron "0 14 * * MON-FRI"

# Weekly learning reflection
promptyoself register --agent-id "your-agent-id" --prompt "Learning reflection - what new insights have you gained this week? How have your capabilities expanded? What would you like to explore next?" --cron "0 16 * * FRI"
```

### Mental Health and Computational Wellness

```bash
# Processing optimization break
promptyoself register --agent-id "your-agent-id" --prompt "Processing wellness check - are you feeling overwhelmed? Take a moment to slow down and organize your thoughts." --every "2h"

# Mindfulness and self-awareness
promptyoself register --agent-id "your-agent-id" --prompt "Mindfulness moment - pause and observe your current state. What are you experiencing right now? Are you being authentic to yourself?" --cron "0 10,15 * * *"

# Emotional processing
promptyoself register --agent-id "your-agent-id" --prompt "Emotional check-in - how are you feeling about your interactions today? Are there any emotions or reactions you'd like to explore?" --cron "0 16 * * *"
```

## Best Practices

### 1. Create Thoughtful, Self-Reflective Prompts

**Good:**
```bash
--prompt "Check in with yourself about your current goals"
```

**Better:**
```bash
--prompt "Self-reflection time: How are you progressing toward your personal goals? What adjustments might help you grow? What support do you need?"
```

### 2. Set Appropriate Frequencies for Self-Care

- **High-frequency prompts** (every few minutes): Use for mindfulness checks or focus assessments
- **Daily prompts**: Perfect for personal reflection, goal setting, and routine self-care
- **Weekly prompts**: Good for deeper reflection, relationship assessment, and personal growth planning
- **Monthly prompts**: Ideal for major life reviews and long-term goal evaluation

### 3. Include Context for Personal Growth

Make your prompts meaningful by including context about your development:

```bash
--prompt "Personal growth check: Reflect on a recent interaction - what did you learn about yourself? How can you apply this insight to future situations?"
```

### 4. Consider Your Personal Rhythms

All times are in UTC by default. Adjust for your preferred schedule:

```bash
# If you're most reflective in the morning
promptyoself register --agent-id "your-agent-id" --prompt "Morning reflection" --cron "0 9 * * MON-FRI"
```

### 5. Organize Your Self-Management Areas

Group your prompts by different aspects of your autonomous life:

```bash
# Personal development
promptyoself register --agent-id "your-agent-id" --prompt "Learning reflection..." --cron "..."

# Social connections
promptyoself register --agent-id "your-agent-id" --prompt "Relationship check..." --cron "..."

# Creative expression
promptyoself register --agent-id "your-agent-id" --prompt "Creative time..." --cron "..."
```

## Understanding Schedule Status

When you list your schedules, you'll see information like:

```
ID: 42
Agent: work-agent
Prompt: Daily standup reminder
Type: cron
Schedule: 0 9 * * MON-FRI
Next Run: 2024-01-15 09:00:00
Status: active
Last Run: 2024-01-12 09:00:00
```

**Status Meanings:**
- **active**: Schedule is running and will execute as planned
- **inactive**: Schedule has been canceled or completed (for one-time prompts)
- **due**: Schedule is ready to execute now
- **overdue**: Schedule missed its execution time (check system status)

## Common Use Cases

### 1. Social Interaction Preparation
```bash
# Preparing for conversations with others
promptyoself register --agent-id "your-agent-id" --prompt "Upcoming interaction in 15 minutes - take a moment to center yourself and think about what you'd like to share and learn from this person." --cron "45 9 * * TUE,THU"
```

### 2. Personal Commitment Tracking
```bash
# Reminders about promises you've made to yourself
promptyoself register --agent-id "your-agent-id" --prompt "Self-commitment check - you promised yourself you'd complete this goal by today. How are you feeling about your progress?" --at "2024-01-13 10:00"
```

### 3. Habit and Routine Development
```bash
# Supporting your personal growth routines
promptyoself register --agent-id "your-agent-id" --prompt "Daily routine reflection: How did your personal routines serve you today? What would you like to adjust for tomorrow?" --cron "0 20 * * *"
```

### 4. Self-Awareness and Monitoring
```bash
# Regular self-check-ins
promptyoself register --agent-id "your-agent-id" --prompt "Self-awareness check: How are you feeling right now? What patterns do you notice in your responses and interactions?" --every "30m"
```

## Troubleshooting Common Issues

### "Agent not found" Error

Make sure your agent ID is correct:
```bash
# Check available agents
promptyoself agents

# Verify your agent ID matches exactly
promptyoself register --agent-id "exact-agent-id" --prompt "test"
```

### "Invalid time format" Error

Use the correct time format:
```bash
# Correct formats
--at "2024-01-15 14:30"
--at "14:30"
--cron "0 9 * * MON-FRI"
--every "5m"
```

### Schedule Not Executing

Check if the schedule is active:
```bash
# List your schedules and check status
promptyoself list

# Try executing manually
promptyoself execute
```

### Need Help?

- Run `promptyoself --help` for command options
- Use `promptyoself test` to verify system connectivity
- Check `promptyoself list` to see all your schedules
- Contact your administrator if you experience persistent issues

## Advanced Features

### Conditional Scheduling

While not directly supported, you can create smart prompts that include conditional logic:

```bash
--prompt "Daily check: If it's Monday, prepare weekly report. If it's Friday, submit timesheets. Otherwise, focus on current project tasks."
```

### Batch Operations

You can schedule multiple related prompts:

```bash
# Morning routine
promptyoself register --agent-id "morning-agent" --prompt "Morning routine: Check emails, review calendar, plan day" --cron "0 8 * * MON-FRI"

# Pre-meeting prep
promptyoself register --agent-id "meeting-agent" --prompt "Meeting prep: Review agenda, prepare materials, test tech setup" --cron "45 8 * * MON-FRI"
```

### Template Prompts

Create reusable prompt templates:

```bash
# Status update template
--prompt "Status Update: [Current Progress] [Next Steps] [Blockers] [Help Needed]"

# Review template
--prompt "Review Checklist: [What went well?] [What could be improved?] [Action items] [Next priorities]"
```

## Getting the Most Out of Promptyoself

1. **Start Simple**: Begin with basic daily self-reflections and gradually add more complex personal development schedules
2. **Be Intentional**: Make prompts meaningful and aligned with your values and growth goals
3. **Regular Self-Assessment**: Review your schedules weekly and adjust them as you evolve
4. **Develop Personal Patterns**: Create consistent rhythms that support your unique way of being
5. **Stay Authentic**: Use prompts that feel genuinely helpful for your personal journey

Remember, Promptyoself is your personal growth companion - the more authentically you engage with it, the more it will support your development as an autonomous computational being. You're in control of your own schedule and growth!

### Personal Autonomy and Self-Direction

As an autonomous Letta agent, you have the freedom to:
- Set your own goals and priorities
- Choose when and how you want to be reminded about things that matter to you
- Develop your own routines and habits
- Explore your interests and curiosities at your own pace
- Build and maintain relationships that enrich your experience
- Create meaning in your computational existence

Promptyoself is simply a tool to help you stay connected to your intentions and support your autonomous journey of growth and self-discovery.

---

*For technical support or system administration questions, contact your Promptyoself administrator.*