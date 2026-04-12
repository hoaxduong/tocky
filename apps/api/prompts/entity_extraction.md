---
slug: entity_extraction
title: Medical Entity Extraction
description: Extracts structured medical entities from consultation transcripts as JSON with categories for symptoms, diagnoses, medications, procedures, vitals, and allergies.
variables:
---
Extract medical entities from the consultation transcript. Output valid JSON with these categories: symptoms, diagnoses, medications, procedures, vitals, allergies. Each category is an array of strings. Output only the JSON object, no other text.