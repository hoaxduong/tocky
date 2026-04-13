"""Sandbox AI client that returns realistic mock responses without calling DashScope.

All mock data is sourced from a real consultation (Type 2 Diabetes diagnosis)
to ensure production-quality, clinically realistic responses during development.
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Transcript segments from real consultation 1f9ab25b-9ced-4ee7-a38c-729ace0f4dc8
# ---------------------------------------------------------------------------
_TRANSCRIPT_SEGMENTS: list[str] = [
    "Hi, Mark. Come on in. Have a seat. Thanks, Dr.",
    "Evans, let me just get your file pulled up here. All right, how have things been since?",
    "We last saw you. Looking at the dates, your last full physical was almost three.",
    "Years ago, before the pandemic. Yeah, I know it's been a while.",
    "Time flies. I've been all right, I suppose. Work's been incredibly.",
    "So mostly I'm just tired. I generally chalked it up to getting older and working.",
    "Too many hours. I hear that a lot. When you say tired, is it an all?",
    "Kind of fatigue, or does it hit you at certain times? Um.",
    "Mostly mid-afternoon, I just crash around two or three p.m. I can barely keep my.",
    "My eyes open at my desk, and, well, I've been waking.",
    "Up a bit more at night, which doesn't help the sleep. Waking up to use the restroom.",
    "Yeah, two or three times a night lately. It's annoying.",
    "Okay, and what about your thirst? Have you found yourself drinking more water?",
    "Or fluids than you used to? Actually, yes, I keep a huge tumbler.",
    "Of water at my desk now, and I feel like I'm refilling it constantly. My mouth just.",
    "Feels dry, I thought it was just the AC in the office being cranked up.",
    "I see. Well, mark those symptoms you're describing the fatigue.",
    "The frequent urination at night, the increased thirst\u2014those piece together very directly.",
    "With the lab results we got back from your blood draw on Tuesday, oh.",
    "Is everything okay? My cholesterol isn't back up, is it?",
    "Cholesterol is actually not too bad. Your LDL is slightly elevated at 110.",
    "But that's manageable. What stood out to me and the reason I wanted you to come in today.",
    "Are your blood sugar levels? My blood sugar? Yes.",
    "We ran two specific tests for that. One is your fasting glucose, which measures the.",
    "Sugar in your blood right at that moment, since you hadn't eaten, a normal level is.",
    "Under 100 milligrams per deciliter, yours came back at 155.",
    "Oh wow, that's high. It is, but the more defining test.",
    "Is called the hemoglobin A1C or just A1C. It gives",
    "Gives us a broad picture of what your average blood sugar has been over the last two to three months.",
    "A normal A1C is below 5.7 percent. Anything between 5.7.",
    "And 6.4 is considered prediabetes. Mark, your A1C came back at.",
    "7.6 percent. Oh, so what does.",
    "That mean exactly based on your symptoms and these two separate lab values being well.",
    "Above the threshold, it means you have type 2 diabetes. Wow.",
    "Okay, I mean, I guess I'm not completely shocked, but it still hits.",
    "It's hard to hear it. I know it's heavy news to take in. It's a major diagnosis.",
    "What makes you say you aren't completely shocked? My mom.",
    "She had type two diabetes. She was diagnosed in her late fifties, I think.",
    "And her dad had it too, but he had it pretty bad. He ended up having to do the shots.",
    "Insulin, I mean. Thank you for sharing that. Genetics do play a very.",
    "Strong role in type two diabetes, having a first degree relative like your mother with the condition.",
    "Significantly increases your risk, so your family history made you heavily predisposed.",
    "To this, so am I going to have to take the shots now? No, no, let's not jump.",
    "Jump ahead to that. For the vast majority of newly diagnosed type 2 diabetics.",
    "We do not start with insulin. We start with lifestyle modifications and oral medications.",
    "But to figure out the best plan for you, I need to understand a bit more about your.",
    "Day to day life. Let's talk about your diet first. Walk me through a typical day of.",
    "Eating, um, well, mornings are rushed. Usually, I'll grab a.",
    "Bagel and a large coffee with cream and sugar on the way to the office. Okay, and lunch?",
    "Lunch is whatever I can get quickly, usually a sandwich from the deli downstairs.",
    "Maybe some chips, or pizza if the team is ordering in, and a soda.",
    "Diet or regular soda? Regular. I don't really like the taste of the diet.",
    "Diet stuff. I probably drink two regular Cokes a day. I understand.",
    "And dinner? My wife and I both work late, so we do plenty of takeout.",
    "Pasta, Thai food, hamburgers\u2014we try to cook a few nights a week, maybe some chicken and.",
    "But it's tough with our schedules. It is incredibly tough. Finding.",
    "Time to cook is a common struggle. Now regarding the sugar and carbohydrates.",
    "Things like bagels, pasta, rice, and especially the regular sodas.",
    "Those break down into glucose very quickly in your bloodstream, and right now your body specifically.",
    "Your pancreas is having trouble producing enough insulin to move that sugar out.",
    "Your blood and into your cells where it belongs, so the sodas have to go. Cutting.",
    "Out liquid sugar is actually the biggest, most impactful change you can make starting today.",
    "If you can switch to water, unsweetened iced tea, or even diet soda, if you have.",
    "You'll immediately reduce the burden on your system. Okay.",
    "I can do that. What about exercise? Honestly, I don't really do much.",
    "I sit at a desk for nine hours a day. I try to walk the dog in the evening.",
    "But it's maybe fifteen minutes. That fifteen minutes is a great foundation.",
    "Exercise is essentially free medicine for diabetes. When your muscles are.",
    "They absorb glucose from your blood without even needing insulin. It makes your whole body.",
    "More sensitive to the insulin you do have, I'd love to see you build that fifty.",
    "15-minute walk up to 30 minutes most days of the week. 30 minutes.",
    "Okay, yeah, my wife would probably love that too. But you mentioned medication earlier.",
    "Yes, because your A1C is at 7.6.",
    "Lifestyle changes alone might not be enough to safely bring you back into range quickly.",
    "I'd like to start you on a medication called metformin. It's the gold.",
    "Standard first line treatment, it's very safe. It's been around for decades, and it works by.",
    "Preventing your liver from releasing too much stored sugar, and makes your muscle cells more.",
    "To insulin, are there side effects? The most common issue is.",
    "An upset stomach or some mild diarrhea when you first begin. To avoid them.",
    "We're going to start you on a low dose, just five hundred milligrams once a day with your largest.",
    "After two weeks, if your stomach is tolerating it well, we'll bump it to twice.",
    "A day. Okay, with dinner, I can remember that.",
    "Do I need to be pricking my finger to check my blood every day? Down the road.",
    "I do want you to monitor your blood sugar a few times a week so we can see how you react to certain.",
    "Foods. I'll write a prescription for a basic glucose meter and some test strips.",
    "But I don't want you to obsess over it right this second. For the next week, your homework is just.",
    "Two things: start the metformin and try to cut out the regular soda. Just.",
    "The pill and dropped the soda. That feels doable.",
    "I was pretty overwhelmed for a minute there. It is completely normal.",
    "To feel overwhelmed, we are not going to fix this in one day. It's a",
    "Marathon, I also want to set you up with an appointment with our clinic's diabetes educator.",
    "She can spend a full hour with you just going over nutrition, reading food labels.",
    "And making realistic meal plans that fit your busy schedule, that would be really.",
    "Helpful, honestly, my wife will probably want to come to that. We highly en.",
    "Encourage spouses to attend. You need a support system. I'm sending the prescription for the.",
    "Metformin and the glucose meter to your pharmacy on file. Let's have you come back for.",
    "Follow up in exactly four weeks. We'll check your weight, see how the medication is settling.",
    "And go from there. All right, thank you, Dr. Evans. I.",
    "Really appreciate you walking me through it. You're very welcome, Mark. Stop at the front desk.",
    "On your way out, to schedule that follow up in the educator appointment, we've got this.",
]

# ---------------------------------------------------------------------------
# SOAP note from the same consultation
# ---------------------------------------------------------------------------
_SOAP_NOTE: dict[str, str] = {
    "subjective": (
        "**Chief Complaint:** Follow-up on recent laboratory results.\n\n"
        "**History of Present Illness:**\n"
        "Patient is a male presenting for follow-up regarding blood work completed "
        "earlier this week. Last comprehensive physical examination was approximately "
        "three years prior. Patient reports generalized fatigue, specifically describing "
        "a mid-afternoon \u201ccrash\u201d (14:00\u201315:00) affecting work performance. Reports "
        "associated sleep disturbance due to nocturia, waking 2\u20133 times per night to "
        "void. Also reports significant polydipsia and xerostomia, noting constant need "
        "to refill water tumbler at work. Patient attributes symptoms initially to age "
        "and work stress.\n\n"
        "**Past Medical History:**\n"
        "*   Hyperlipidemia (previously noted, currently manageable).\n"
        "*   No prior diagnosis of diabetes mellitus.\n\n"
        "**Family History:**\n"
        "*   Mother: Type 2 Diabetes Mellitus (diagnosed late 50s).\n"
        "*   Maternal Grandfather: Type 2 Diabetes Mellitus (required insulin therapy).\n\n"
        "**Social History:**\n"
        "*   **Occupation:** Sedentary desk job (9 hours/day).\n"
        "*   **Diet:** High in refined carbohydrates and added sugars. Typical intake "
        "includes bagel with sugary coffee (breakfast), deli sandwich/pizza with regular "
        "soda (lunch, 2 cans/day), and frequent takeout dinners (pasta, Thai, hamburgers).\n"
        "*   **Exercise:** Minimal; reports walking dog for approximately 15 minutes daily.\n"
        "*   **Tobacco/Alcohol:** Not discussed.\n\n"
        "**Review of Systems:**\n"
        "*   **Constitutional:** Positive for fatigue.\n"
        "*   **Endocrine:** Positive for polydipsia.\n"
        "*   **Genitourinary:** Positive for nocturia (2\u20133 times/night)."
    ),
    "objective": (
        "**Laboratory Results:**\n"
        "*   **Fasting Plasma Glucose:** 155 mg/dL (Reference: <100 mg/dL).\n"
        "*   **Hemoglobin A1C:** 7.6% (Reference: <5.7%; Diabetes \u22656.5%).\n"
        "*   **Lipid Panel:** LDL 110 mg/dL (Slightly elevated).\n\n"
        "**Physical Examination:**\n"
        "*   Vitals and physical exam findings not explicitly documented in transcript."
    ),
    "assessment": (
        "1.  **Type 2 Diabetes Mellitus:** Newly diagnosed. Diagnosis confirmed based on "
        "symptomatic presentation (polyuria, polydipsia, fatigue) and diagnostic criteria "
        "(Fasting glucose >126 mg/dL and A1C \u22656.5%).\n"
        "2.  **Hyperlipidemia:** LDL mildly elevated but currently considered manageable.\n"
        "3.  **Lifestyle Factors:** Sedentary behavior and diet high in glycemic load "
        "contributing to metabolic dysregulation."
    ),
    "plan": (
        "**Medication:**\n"
        "*   **Metformin:** 500 mg PO once daily with the largest meal (dinner) to "
        "minimize GI side effects.\n"
        "*   **Titration:** Increase to 500 mg PO BID after 2 weeks if tolerated.\n"
        "*   **Prescriptions:** Sent to pharmacy on file.\n\n"
        "**Lifestyle Modifications:**\n"
        "*   **Diet:** Eliminate sugar-sweetened beverages (regular soda) immediately. "
        "Substitute with water, unsweetened iced tea, or diet soda. Reduce refined "
        "carbohydrate intake (bagels, pasta, white rice).\n"
        "*   **Exercise:** Increase daily physical activity. Goal: Extend dog walk to "
        "30 minutes most days of the week.\n\n"
        "**Monitoring:**\n"
        "*   **Home Glucose Monitoring:** Prescription provided for glucose meter and "
        "test strips. Instructed to check blood glucose a few times per week to assess "
        "response to dietary changes and medication.\n"
        "*   **Weight:** Will be monitored at follow-up.\n\n"
        "**Referrals:**\n"
        "*   **Diabetes Educator:** Appointment to be scheduled for comprehensive "
        "nutrition counseling, label reading education, and meal planning. Spouse "
        "encouraged to attend.\n\n"
        "**Follow-up:**\n"
        "*   Return to clinic in 4 weeks.\n"
        "*   Assess medication tolerance, weight changes, and review home glucose logs.\n"
        "*   Schedule appointments at front desk prior to departure."
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
        "increased thirst",
        "dry mouth",
        "crashing mid-afternoon",
    ],
    "diagnoses": ["Type 2 diabetes"],
    "medications": ["Metformin"],
    "procedures": [
        "Blood draw",
        "Fasting glucose test",
        "Hemoglobin A1C test",
        "Glucose monitoring",
        "Diabetes educator appointment",
    ],
    "vitals": ["LDL 110", "Fasting glucose 155", "A1C 7.6 percent"],
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
            "title": "Type 2 Diabetes Diagnosis and Initial Management Discussion",
            "patient_identifier": "Mark",
        }

    async def close(self) -> None:
        pass
