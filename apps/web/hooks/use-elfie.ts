"use client"

import { useMutation, useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

export interface ElfieVitalReading {
  date: string
  value: number
  unit: string
}

export interface ElfieBloodPressureReading {
  date: string
  systolic: number
  diastolic: number
}

export interface ElfieVitals {
  glucose: ElfieVitalReading[]
  blood_pressure: ElfieBloodPressureReading[]
  weight: ElfieVitalReading[]
}

export interface ElfieMedication {
  name: string
  dose: string
  frequency: string
  adherence_pct: number
  missed_last_7d: number
}

export interface ElfieLifestyleStats {
  avg_daily_steps: number
  avg_sleep_hours: number
  avg_calories: number
}

export interface ElfiePatientData {
  patient_identifier: string
  name: string
  age: number
  conditions: string[]
  member_since: string
  adherence_score: number
  vitals: ElfieVitals
  medications: ElfieMedication[]
  lifestyle: ElfieLifestyleStats
  elfie_coins: number
  tier: string
}

export interface ElfieCarePlanItem {
  category: string
  action: string
  details: string
}

interface ElfieCarePlanRequest {
  consultation_id: string
  patient_identifier: string
  items: ElfieCarePlanItem[]
}

interface ElfiePushResult {
  success: boolean
  notification_id: string
  message: string
}

export function useElfiePatient(patientIdentifier: string | null) {
  return useQuery({
    queryKey: ["elfie-patient", patientIdentifier],
    queryFn: () =>
      apiFetch<ElfiePatientData>(
        `/api/v1/elfie/patient/${encodeURIComponent(patientIdentifier!)}`
      ),
    enabled: !!patientIdentifier,
    staleTime: 5 * 60 * 1000,
    retry: false,
  })
}

export function usePushToElfie() {
  return useMutation({
    mutationFn: (request: ElfieCarePlanRequest) =>
      apiFetch<ElfiePushResult>("/api/v1/elfie/push-care-plan", {
        method: "POST",
        body: JSON.stringify(request),
      }),
  })
}
