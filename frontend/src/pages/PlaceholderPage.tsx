interface PlaceholderPageProps {
  title: string
  description: string
}

export function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <section className="page">
      <div className="page-header">
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <article className="card muted">Coming in a later phase.</article>
    </section>
  )
}