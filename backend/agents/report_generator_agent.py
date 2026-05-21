import json
import os
import asyncio
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import edge_tts
from backend.agents.base_agent import BaseQuantAgent
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class ReportGeneratorAgent(BaseQuantAgent):
    async def _run(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            report_data = {
                "technical": context.get('technical_result'),
                "fundamental": context.get('fundamental_result'),
                "sentiment": context.get('sentiment_result'),
                "risk": context.get('risk_result')
            }
            
            prompt = (
                f"Generate a professional executive summary for this report: {json.dumps(report_data)}\n\n"
                f"--- MANDATORY SECTIONS ---\n"
                f"1. MIROFISH PREDICTIVE SIMULATION: Highlight the institutional agent behavior and emergent patterns.\n"
                f"2. WORLDMONITOR SITUATIONAL AWARENESS: Highlight the macro 7-signal composite risk.\n"
                f"3. FINAL VERDICT: A synthesis of all signals."
            )
            summary = await self.model_router.route("general_analysis", prompt, "You are a senior financial intelligence writer specializing in deep predictive analytics.")
            report_data['executive_summary'] = summary
            
            env = Environment(loader=FileSystemLoader("templates"))
            try:
                template = env.get_template("report_template.html")
                html_out = template.render(data=report_data)
                pdf_path = f"./data_cache/reports/report_{int(asyncio.get_event_loop().time())}.pdf"
                os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
                HTML(string=html_out).write_pdf(pdf_path)
            except Exception as e:
                logger.error(f"PDF generation failed: {e}")
                pdf_path = None
                
            audio_path = f"./data_cache/audio/summary_{int(asyncio.get_event_loop().time())}.mp3"
            os.makedirs(os.path.dirname(audio_path), exist_ok=True)
            try:
                communicate = edge_tts.Communicate(summary, "en-US-ChristopherNeural")
                await communicate.save(audio_path)
            except Exception as e:
                logger.error(f"TTS generation failed: {e}")
                audio_path = None
                
            return {
                "summary": summary,
                "pdf_path": pdf_path,
                "audio_path": audio_path
            }
        except Exception as e:
            logger.error(f"ReportGeneratorAgent failed: {e}")
            return {"error": str(e)}
