"""Sandbox AI client that returns realistic mock responses without calling DashScope.

All mock data is sourced from a real consultation (Type 2 Diabetes diagnosis)
to ensure production-quality, clinically realistic responses during development.
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Transcript segments from real consultation 63d9d4b1-ac97-4cf6-8c75-2bda0c58c581
# ---------------------------------------------------------------------------
_TRANSCRIPT_SEGMENTS: list[str] = [
    "Hi, Mark. Come on in. Have a seat.",
    "Thanks, Dr. Evans. Let me just get your file pulled up here.",
    "All right, how have things been since we last saw you? Looking at the dates, your last full physical was almost three years ago, before the pandemic. Yeah, I know it's been a while. Time flies. I've been all right, I suppose. Work's been incredibly busy, so mostly I'm just tired. I generally chalked it up to getting older and working too many hours. I hear that a lot.",
    "When you say tired, is it an all-day kind of fatigue or does it hit you at certain times?",
    "Um, mostly mid-afternoon. I just crash around two or three p.m. I can barely keep my eyes open at my desk, and, well, I've been waking up a bit more at night, which doesn't help the sleep. Waking up to use the restroom.",
    "Yeah, two or three times a night lately. It's annoying. Okay, and what about your thirst? Have you found yourself drinking more water or fluids than you used to?",
    "Actually, yes. I keep a huge tumbler of water at my desk now, and I feel like I'm refilling it constantly. My mouth just feels dry. I thought it was just the AC in the office being cranked up. I see.",
    "Well, Mark, those symptoms you're describing\u2014the fatigue, the frequent urination at night, the increased thirst\u2014those piece together very directly with the lab results we got back from your blood draw on Tuesday.",
    "Oh, is everything okay? My cholesterol isn't back up, is it?",
    "Your cholesterol is actually not too bad, your LDL is slightly elevated at one hundred and ten, but that's manageable.",
    "What stood out to me and the reason I wanted you to come in today are your blood sugar levels. My blood sugar, yes.",
    "We ran two specific tests for that. One is your fasting glucose, which measures the sugar in your blood right at that moment since you hadn't eaten.",
    "A normal level is under 100 milligrams per deciliter. Yours came back at 155. Oh wow, that's high. It is.",
    "But the more defining test is called the hemoglobin A1C, or just A1C. It gives us a broad picture of what your average blood sugar has been over the last two to three months. A normal A1C is below 5.7%. Anything between 5.7 and 6.4 is considered prediabetes. Mark, your A1C came back at 7.6%.",
    "Oh, so.",
    "What does that mean exactly? Based on your symptoms and these two separate lab values being well above the threshold, it means you have type 2 diabetes. Wow. Okay. I mean, I guess I'm not completely shocked, but it still hits hard to hear it. I know it's heavy news to take in. It's a major diagnosis.",
    "What makes you say you aren't completely shocked?",
    "My mom, she had type two diabetes. She was diagnosed in her late fifties, I think, and her dad had it too, but he had it pretty bad. He ended up having to do the shots, insulin, I mean. Thank you for sharing that.",
    "Genetics do play a very strong role in type 2 diabetes. Having a first-degree relative like your mother with the condition significantly increases your risk. So your family history made you heavily predisposed to this. So am I going to have to take the shots now? No, no, let's not jump ahead to that.",
    "For the vast majority of newly diagnosed type 2 diabetics, we do not start with insulin. We start with lifestyle modifications and oral medication. But to figure out the best plan for you, I need to understand a bit more about your day-to-day life.",
    "Let's talk about your diet first. Walk me through a typical day of eating. Um, well, mornings are rushed. Usually, I'll grab a bagel and a large coffee with cream and sugar on the way to the office. Okay, and lunch?",
    "Lunch is whatever I can get quickly. Usually a sandwich from the deli downstairs, maybe some chips, or pizza if the team is ordering in, and a soda. Diet or regular soda? Regular. I don't really like the taste of the diet stuff. I probably drink two regular Cokes a day. I understand. And dinner?",
    "My wife and I both work late, so we do plenty of takeout\u2014pasta, Thai food, hamburgers. We try to cook a few nights a week, maybe some chicken and rice, but it's tough with our schedules. It is incredibly tough.",
    "Finding time to cook is a common struggle. Now, regarding the sugar and carbohydrates, things like bagels, pasta, rice, and especially the regular sodas.",
    "Those break down into glucose very quickly in your bloodstream, and right now your body, specifically your pancreas, is having trouble producing enough insulin to move that sugar out of your blood and into your cells where it belongs. So the sodas have to go. Cutting out liquid sugar is actually the biggest, most impactful change you can make starting today.",
    "If you can switch to water, unsweetened iced tea, or even diet soda if you have to, you'll immediately reduce the burden on your system. Okay, I can do that.",
    "What about exercise? Honestly, I don't really do much. I sit at a desk for nine hours a day. I try to walk the dog in the evenings, but it's maybe fifteen minutes. That fifteen minutes is a great foundation. Exercise is essentially free medicine for diabetes.",
    "When your muscles are active, they absorb glucose from your blood without even needing insulin. It makes your whole body more sensitive to the insulin you do have.",
    "I'd love to see you build that fifteen-minute walk up to thirty minutes most days of the week.",
    "Thirty minutes, okay? Yeah, my wife would probably love that too. But you mentioned medication earlier. Yes, because your A1C is at 7.6, lifestyle changes alone might not be enough to safely bring you back into range quickly.",
    "I'd like to start you on a medication called metformin. It's the gold standard first line treatment. It's very safe. It's been around for decades and it works by preventing your liver from releasing too much stored sugar and makes your muscle cells more responsive to insulin.",
    "Are there side effects? The most common issue is an upset stomach or some mild diarrhea when you first begin.",
    "To avoid that, we're going to start you on a low dose, just 500 milligrams once a day with your largest meal.",
    "After two weeks, if your stomach is tolerating it well, we'll bump it to twice a day.",
    "Okay, with dinner, I can remember that. Do I need to be pricking my finger to check my blood every day? Down the road, I do want you to monitor your blood sugar a few times a week so we can see how you react to certain foods.",
    "I'll write a prescription for a basic glucose meter and some test strips, but I don't want you to obsess over it right this second.",
    "For the next week, your homework is just two things: start the metformin and try to cut out the regular soda.",
    "Just the pill and drop the soda.",
    "That feels doable.",
    "I was pretty overwhelmed for a minute there. It is completely normal to feel overwhelmed.",
]

# ---------------------------------------------------------------------------
# SOAP note from the same consultation
# ---------------------------------------------------------------------------
_SOAP_NOTE: dict[str, str] = {
    "subjective": (
        "**Chief Complaint:** Follow-up on laboratory results and fatigue.\n\n"
        "**History of Present Illness:**\n"
        "Patient is a male presenting for follow-up regarding recent blood work. "
        "Reports a three-year gap since last comprehensive physical examination. "
        "Patient describes persistent fatigue, characterized by significant "
        "mid-afternoon energy crashes (14:00\u201315:00). Reports sleep disturbance "
        "due to nocturia, waking 2\u20133 times nightly to void. Endorses polydipsia "
        "and xerostomia, noting constant need to refill water container throughout "
        "the workday. Patient attributes symptoms initially to age and work stress.\n\n"
        "**Past Medical History:**\n"
        "Hyperlipidemia (previously monitored).\n\n"
        "**Family History:**\n"
        "Significant for Type 2 Diabetes Mellitus in mother (diagnosed late 50s) "
        "and maternal grandfather (required insulin therapy).\n\n"
        "**Social History:**\n"
        "Employed in sedentary desk position (9 hours/day). Dietary habits include "
        "high intake of refined carbohydrates and sugars: daily bagel with sweetened "
        "coffee, deli sandwiches or pizza for lunch, and two regular sodas daily. "
        "Dinner frequently consists of takeout (pasta, Thai, hamburgers). Physical "
        "activity is limited to a 15-minute evening dog walk. Denies tobacco use; "
        "alcohol use not discussed.\n\n"
        "**Review of Systems:**\n"
        "*   **Constitutional:** Positive for fatigue.\n"
        "*   **Endocrine:** Positive for polydipsia.\n"
        "*   **Genitourinary:** Positive for nocturia.\n"
        "*   **Neurological:** Denies numbness or tingling (not explicitly discussed, "
        "but no complaints voiced)."
    ),
    "objective": (
        "**Laboratory Results (Reviewed from blood draw on Tuesday):**\n"
        "*   **Fasting Plasma Glucose:** 155 mg/dL (Reference: <100 mg/dL).\n"
        "*   **Hemoglobin A1C:** 7.6% (Reference: <5.7%; Diabetes diagnostic "
        "threshold \u22656.5%).\n"
        "*   **LDL Cholesterol:** 110 mg/dL (Slightly elevated).\n\n"
        "**Physical Examination:**\n"
        "*   Vitals and physical exam findings not documented in provided transcript."
    ),
    "assessment": (
        "1.  **Type 2 Diabetes Mellitus:** Newly diagnosed. Diagnosis supported by "
        "symptomatic presentation (polydipsia, nocturia, fatigue) and confirmatory "
        "laboratory values (Fasting Glucose 155 mg/dL, A1C 7.6%). Strong genetic "
        "predisposition noted.\n"
        "2.  **Hyperlipidemia:** LDL mildly elevated at 110 mg/dL.\n"
        "3.  **Lifestyle Risk Factors:** Sedentary behavior, diet high in refined "
        "carbohydrates and sugar-sweetened beverages."
    ),
    "plan": (
        "**Medication:**\n"
        "*   **Metformin:** Initiate 500 mg PO once daily with the largest meal "
        "(dinner) to minimize gastrointestinal side effects.\n"
        "*   **Titration:** Increase to 500 mg PO BID after two weeks if tolerated.\n"
        "*   **Supply:** Prescription provided.\n\n"
        "**Diagnostics/Monitoring:**\n"
        "*   **Home Glucose Monitoring:** Prescribed glucometer and test strips. "
        "Instructed to check blood glucose a few times per week to assess response "
        "to dietary changes and medication. Advised against obsessive monitoring "
        "initially.\n"
        "*   **Follow-up Labs:** Repeat A1C and metabolic panel to be scheduled per "
        "standard diabetes care guidelines (typically 3 months).\n\n"
        "**Lifestyle Modifications:**\n"
        "*   **Diet:** Eliminate sugar-sweetened beverages (regular soda) immediately. "
        "Substitute with water, unsweetened iced tea, or diet soda. Reduce refined "
        "carbohydrate intake (bagels, pasta, white rice).\n"
        "*   **Exercise:** Increase physical activity from 15 minutes to 30 minutes "
        "of walking most days of the week.\n\n"
        "**Education:**\n"
        "*   Discussed pathophysiology of Type 2 Diabetes and insulin resistance.\n"
        "*   Reviewed potential side effects of Metformin (GI upset, diarrhea) and "
        "mitigation strategies (taking with food, slow titration).\n"
        "*   Addressed patient concerns regarding insulin therapy; clarified that "
        "oral medication and lifestyle changes are first-line treatment.\n"
        "*   Patient verbalized understanding of plan and expressed readiness to "
        "implement changes."
    ),
}

# ---------------------------------------------------------------------------
# Medical entities from the same consultation
# ---------------------------------------------------------------------------
_MEDICAL_ENTITIES: dict = {
    "symptoms": [
        "tired",
        "fatigue",
        "waking up at night",
        "waking up to use the restroom",
        "frequent urination",
        "increased thirst",
        "drinking more water",
        "dry mouth",
    ],
    "diagnoses": ["type 2 diabetes"],
    "medications": ["metformin", "insulin"],
    "procedures": [
        "full physical",
        "blood draw",
        "fasting glucose",
        "hemoglobin A1C",
        "monitor blood sugar",
    ],
    "vitals": ["LDL 110", "fasting glucose 155", "A1C 7.6%"],
    "allergies": [],
}


class SandboxAIClient:
    """Drop-in replacement for DashScopeClient that returns canned responses."""

    def __init__(self, latency: float = 0.2) -> None:
        self.latency = latency
        self._call_counter = 0

    async def transcribe_audio(self, audio_bytes: bytes, language: str) -> str:
        await asyncio.sleep(self.latency)
        segment = _TRANSCRIPT_SEGMENTS[self._call_counter % len(_TRANSCRIPT_SEGMENTS)]
        self._call_counter += 1
        logger.debug("sandbox transcribe_audio [%d]: %s", self._call_counter, segment[:60])
        return segment

    async def classify_relevance(self, text: str, language: str) -> bool:
        await asyncio.sleep(self.latency * 0.5)
        relevant = len(text.strip()) >= 10
        logger.debug("sandbox classify_relevance: %s -> %s", text[:40], relevant)
        return relevant

    async def generate_soap(
        self, transcript_text: str, language: str
    ) -> dict[str, str]:
        await asyncio.sleep(self.latency * 2)
        logger.debug("sandbox generate_soap: %d chars input", len(transcript_text))
        return dict(_SOAP_NOTE)

    async def review_soap(
        self,
        transcript_text: str,
        soap: dict[str, str],
        language: str,
    ) -> list[dict]:
        await asyncio.sleep(self.latency)
        logger.debug("sandbox review_soap: no flags")
        return []

    async def extract_medical_entities(self, text: str, language: str) -> dict:
        await asyncio.sleep(self.latency)
        logger.debug("sandbox extract_medical_entities")
        return dict(_MEDICAL_ENTITIES)

    async def detect_language(self, text: str) -> str:
        await asyncio.sleep(self.latency * 0.3)
        logger.debug("sandbox detect_language -> en")
        return "en"

    async def extract_consultation_metadata(
        self, transcript_text: str
    ) -> dict[str, str]:
        await asyncio.sleep(self.latency * 0.5)
        logger.debug("sandbox extract_consultation_metadata")
        return {
            "title": "Diagnosis and initial management of type 2 diabetes",
            "patient_identifier": "Mark",
        }

    async def close(self) -> None:
        pass
