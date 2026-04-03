from datetime import datetime, timedelta
from telegram.ext import MessageHandler, filters
import json
import os
from dotenv import load_dotenv
from telegram import Update
load_dotenv()
from telegram.ext import Application, CommandHandler, ContextTypes

TASKS_FILE = "tasks.json"


# ---------- Utility Functions ----------

def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return {}
    with open(TASKS_FILE, "r") as f:
        return json.load(f)


def save_tasks(tasks):
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=4)


def get_user_tasks(user_id):
    tasks = load_tasks()
    return tasks.get(str(user_id), [])


def update_user_tasks(user_id, user_tasks):
    tasks = load_tasks()
    tasks[str(user_id)] = user_tasks
    save_tasks(tasks)


# ---------- Command Handlers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Shah’s Daily Planner!\n\n"
        "Commands:\n"
        "/add Category | Task\n"
        "/list\n"
        "/done <task #>\n"
        "/progress\n"
        "/remind <task #> <minutes>"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().strip()

    # ADD
    if text.startswith("add "):
        context.args = text[4:].split()
        await add_task(update, context)
        return

    # LIST
    if text in ["list", "show", "show tasks", "list tasks"]:
        await list_tasks(update, context)
        return

    # DONE
    if text.startswith("done "):
        context.args = text.split()[1:]
        await done_task(update, context)
        return

    # PROGRESS
    if text.startswith("progress "):
        context.args = text.split()[1:]
        await set_progress(update, context)
        return

    # REMIND
    if text.startswith("remind "):
        context.args = text.split()[1:]
        await remind(update, context)
        return

    # fallback help
    await update.message.reply_text(
        "I didn't understand.\n"
        "Try:\n"
        "add Buy groceries\n"
        "list\n"
        "done 1\n"
        "progress 1 50\n"
        "remind 1 30"
    )

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /remind <task #> <minutes>"
        )
        return

    try:
        index = int(context.args[0]) - 1
        minutes = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Invalid format.")
        return

    user_tasks = get_user_tasks(user_id)

    if index < 0 or index >= len(user_tasks):
        await update.message.reply_text("Task not found.")
        return

    task = user_tasks[index]

    # schedule reminder
    context.job_queue.run_once(
        send_reminder,
        when=minutes * 60,
        data={
            "chat_id": update.effective_chat.id,
            "task": task["text"],
            "category": task.get("category", "General")
        }
    )

    await update.message.reply_text(
        f"⏰ Reminder set for '{task['text']}' in {minutes} minutes"
    )

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job

    await context.bot.send_message(
        chat_id=job.data["chat_id"],
        text=f"🔔 Reminder\n\n[{job.data['category']}] {job.data['task']}"
    )

async def set_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /progress <task #> <percent>"
        )
        return
    
    try:
        index = int(context.args[0]) - 1
        percent = int(context.args[1])
    except:
        await update.message.reply_text("Invalid format")
        return
    
    if percent < 0 or percent > 100:
        await update.message.reply_text("Percent must be 0-100")
        return
    
    user_tasks = get_user_tasks(user_id)

    if index < 0 or index >= len(user_tasks):
        await update.message.reply_text("Task not found")
        return
    
    user_tasks[index]["progress"] = percent

    if percent == 100:
        user_tasks[index]["done"] = True

    update_user_tasks(user_id, user_tasks)

    await update.message.reply_text(
        f"📊 Updated: {user_tasks[index]['text']}  → {percent}%"
    )

from datetime import datetime

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text(
            "Usage: /add Category | Task"
        )
        return

    text = " ".join(context.args)

    if "|" not in text:
        await update.message.reply_text(
            "Format: /add Work | Finish report"
        )
        return

    category, task_text = [x.strip() for x in text.split("|", 1)]

    user_tasks = get_user_tasks(user_id)

    user_tasks.append({
        "text": task_text,
        "category": category,
        "done": False,
        "progress": 0,
        "created": datetime.now().isoformat()
    })

    update_user_tasks(user_id, user_tasks)

    await update.message.reply_text(
        f"✅ Added [{category}] {task_text}"
    )

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_tasks = get_user_tasks(user_id)

    if not user_tasks:
        await update.message.reply_text("No tasks yet.")
        return

    # group tasks by category
    categories = {}

    for i, task in enumerate(user_tasks, 1):
        category = task.get("category", "General")

        if category not in categories:
            categories[category] = []

        categories[category].append((i, task))

    message = "📋 Your Tasks\n\n"

    # display grouped
    for category, tasks in categories.items():

        message += f"📁 {category}\n"

        for i, task in tasks:
            progress = task.get("progress", 0)

            if task.get("done"):
                status = "✅"
                progress = 100
            else:
                status = "⬜"

            message += f"{i}. {status} {task['text']} ({progress}%)\n"

        message += "\n"

    await update.message.reply_text(message)

async def done_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /done <task_number>")
        return

    try:
        task_index = int(context.args[0]) - 1
    except ValueError:
        await update.message.reply_text("Please provide a valid task number.")
        return

    user_tasks = get_user_tasks(user_id)

    if task_index < 0 or task_index >= len(user_tasks):
        await update.message.reply_text("Task number out of range.")
        return

    user_tasks[task_index]["done"] = True
    update_user_tasks(user_id, user_tasks)

    await update.message.reply_text(
        f"🎉 Marked as done: {user_tasks[task_index]['text']}"
    )


# ---------- Main ----------

def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_task))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("done", done_task))
    app.add_handler(CommandHandler("progress", set_progress))
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot is running...")
    app.run_polling(drop_pending_updates=True, stop_signals=None)


if __name__ == "__main__":
    main()
