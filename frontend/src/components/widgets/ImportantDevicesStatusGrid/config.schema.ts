import { z } from 'zod'

export const importantDevicesGridConfigSchema = z.object({
  title: z.string().default('Important Devices'),
  maxItems: z.number().min(1).max(50).default(12),
  refreshIntervalSec: z.number().min(5).default(30),
})

export type ImportantDevicesGridConfig = z.infer<typeof importantDevicesGridConfigSchema>