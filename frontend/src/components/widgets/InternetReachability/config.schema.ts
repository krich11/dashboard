import { z } from 'zod'

export const internetReachabilityConfigSchema = z.object({
  title: z.string().default('Internet Health'),
  showTargets: z.boolean().default(true),
  refreshIntervalSec: z.number().min(5).default(30),
})

export type InternetReachabilityConfig = z.infer<typeof internetReachabilityConfigSchema>

export const defaultInternetReachabilityConfig: InternetReachabilityConfig = {
  title: 'Internet Health',
  showTargets: true,
  refreshIntervalSec: 30,
}