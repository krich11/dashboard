import { z } from 'zod'

export const inventoryTableConfigSchema = z.object({
  title: z.string().default('Inventory'),
  maxRows: z.number().min(1).max(100).default(20),
  refreshIntervalSec: z.number().min(5).default(30),
})

export type InventoryTableConfig = z.infer<typeof inventoryTableConfigSchema>