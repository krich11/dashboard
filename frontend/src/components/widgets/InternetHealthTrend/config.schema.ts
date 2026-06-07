import { z } from 'zod'

export const internetHealthTrendConfigSchema = z.object({
  title: z.string().default('Internet Health Trend'),
  hours: z.number().min(1).max(168).default(24),
  refreshIntervalSec: z.number().min(5).default(60),
})

export type InternetHealthTrendConfig = z.infer<typeof internetHealthTrendConfigSchema>