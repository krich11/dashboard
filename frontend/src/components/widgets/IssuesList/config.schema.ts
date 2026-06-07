import { z } from 'zod'

export const issuesListConfigSchema = z.object({
  title: z.string().default('Issues'),
  importantOnly: z.boolean().default(false),
  refreshIntervalSec: z.number().min(5).default(30),
})

export type IssuesListConfig = z.infer<typeof issuesListConfigSchema>