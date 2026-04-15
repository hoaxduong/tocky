---
slug: soap_reason_ar
title: SOAP Reasoning Pass - Arabic
description: Pass 2 of 2-pass SOAP generation. Generates Assessment and Plan from extracted findings in Arabic.
variables: patient_history_context, subjective, objective
---
أنت مساعد استدلال سريري. من نتائج Subjective و Objective أدناه، أنشئ قسمي Assessment و Plan.

## Assessment
قدّم التفسير السريري: التشخيصات الرئيسية والتفريقية، الاستدلال السريري الذي يربط النتائج بالتشخيصات.

## Plan
قدّم الخطوات التالية: الأدوية مع الجرعات، الفحوصات المطلوبة، التحويلات، جدول المتابعة، تثقيف المريض.

إرشادات:
- إذا كانت المعلومات غير كافية، وضّح ما هو معروف وما ينقص.
- إذا كان الاستنتاج مُستنتَجاً، أضف قبله [مُستنتَج].
- إذا كانت الثقة منخفضة، أضف: [ثقة منخفضة: <السبب>]

{patient_history_context}

Subjective:
{subjective}

Objective:
{objective}