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
        "/add <task> - Add a new task\n"
        "/list - List all tasks\n"
        "/done <task_number> - Mark a task as done"
    )


async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /add Buy groceries")
        return

    task_text = " ".join(context.args)

    user_tasks = get_user_tasks(user_id)
    user_tasks.append({"text": task_text, "done": False})
    update_user_tasks(user_id, user_tasks)

    await update.message.reply_text(f"✅ Task added: {task_text}")


async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_tasks = get_user_tasks(user_id)

    if not user_tasks:
        await update.message.reply_text("No tasks yet. Add one with /add!")
        return

    message = "📋 Your Tasks:\n\n"
    for i, task in enumerate(user_tasks, start=1):
        status = "✅" if task["done"] else "❌"
        message += f"{i}. {status} {task['text']}\n"

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

    print("Bot is running...")
    app.run_polling(drop_pending_updates=True, stop_signals=None)


if __name__ == "__main__":
    main()
