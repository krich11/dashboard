import { z } from 'zod'

export const upDownConfigSchema = z.object({
  title: z.string().default('Datacenter Status'),
  showBreakdown: z.boolean().default(true),
  refreshIntervalSec: z.number().min(5).default(30),
})

export type UpDownConfig = z.infer<typeof upDownConfigSchema>

export const defaultUpDownConfig: UpDownConfig = {
  title: 'Datacenter Status',
  showBreakdown: true,
  refreshIntervalSec: 30,
}