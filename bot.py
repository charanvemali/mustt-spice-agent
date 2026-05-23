import os
import re
import json
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# =====================================================================
# SYSTEM INITIALIZATION
# =====================================================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_KEY")
GOOGLE_WEBAPP_URL = os.environ.get("WEBAPP_URL")

genai.configure(api_key=GEMINI_API_KEY)

def tool_research_agent_search(spice_type: str, sourcing_location: str) -> str:
    """Uses real-time web grounding to extract wholesale spice handlers."""
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        tools={"google_search": {}}
    )
    system_instruction = (
        f"Discover 5 real wholesale companies, their primary operating city, "
        f"and contact phone numbers for the spice '{spice_type}'. "
        f"Format output strictly as a JSON list: "
        f"[{{\"name\": \"...\", \"hub\": \"...\", \"phone\": \"...\", \"est_year\": 2012}}]."
    )
    query = f"Wholesale bulk {spice_type} suppliers or processing mills in {sourcing_location}"
    response = model.generate_content(f"{system_instruction}\n\nQuery: {query}")
    return response.text

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_command = update.message.text
    await update.message.reply_text("🧠 *Processing instructions across spice hubs...*")
    
    master_orchestrator = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        tools=[tool_research_agent_search]
    )
    
    try:
        execution_payload = master_orchestrator.generate_content(user_command)
        
        if execution_payload.candidates[0].function_calls:
            for call in execution_payload.candidates[0].function_calls:
                if call.name == "tool_research_agent_search":
                    await update.message.reply_text("⚡ *Dispatched Sourcing Agent across web registries...*")
                    
                    raw_data = tool_research_agent_search(**call.args)
                    # Safe regex parsing to strip markdown blocks cleanly
                    clean_json = raw_data.replace("```json", "").replace("
```", "").strip()
                    suppliers = json.loads(clean_json)
                    
                    spice_context = call.args.get("spice_type", "General").title()
                    current_year = datetime.now().year
                    inserted = 0
                    
                    for sup in suppliers:
                        experience = current_year - int(sup.get("est_year", current_year))
                        score = min(10.0, float(experience * 0.4) + 5.5)
                        
                        payload = {
                            "spice_type": spice_context,
                            "name": sup.get("name"),
                            "hub": sup.get("hub"),
                            "phone": sup.get("phone"),
                            "scale": "Large Scale" if experience > 10 else "Medium Scale",
                            "est_year": f"{experience} Years",
                            "status": "Prospect Lead",
                            "score": round(score, 1)
                        }
                        
                        requests.post(GOOGLE_WEBAPP_URL, json=payload)
                        inserted += 1
                        
                    await update.message.reply_text(f"✅ Mission complete! Created tab and updated {inserted} vendors under '{spice_context}_Sourcing'.")
        else:
            await update.message.reply_text(execution_payload.text)
            
    except Exception as e:
        await update.message.reply_text(f"❌ System anomaly: {str(e)}")

if __name__ == "__main__":
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()
