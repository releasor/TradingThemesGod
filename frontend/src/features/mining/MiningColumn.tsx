import type { MiningCardItem } from '@/types/mining'
import { MiningCard } from '@/features/mining/MiningCard'

interface MiningColumnProps {
  title: string
  cards: MiningCardItem[]
  emptyLabel: string
  showNoteButton?: boolean
  testId: string
}

export function MiningColumn({
  title,
  cards,
  emptyLabel,
  showNoteButton = false,
  testId,
}: MiningColumnProps) {
  return (
    <section
      data-testid={testId}
      className="flex min-h-[12rem] flex-col rounded-xl border border-border/60 bg-background/40"
      aria-labelledby={`${testId}-heading`}
    >
      <header className="flex items-center justify-between gap-2 border-b border-border/50 px-4 py-3">
        <h2 id={`${testId}-heading`} className="text-sm font-semibold tracking-tight">
          {title}
        </h2>
        <span className="text-xs tabular-nums text-muted-foreground">{cards.length}</span>
      </header>

      <div className="flex flex-1 flex-col gap-3 p-3 sm:p-4">
        {cards.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">{emptyLabel}</p>
        ) : (
          cards.map((card) => (
            <MiningCard key={card.id} card={card} showNoteButton={showNoteButton} />
          ))
        )}
      </div>
    </section>
  )
}
