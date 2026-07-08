import { useMemo } from "react";
import { Responsive, WidthProvider, type Layout } from "react-grid-layout";
import { motion } from "framer-motion";
import ChartCard from "./ChartCard";
import type { Palette } from "../lib/theme";
import type { IntentCard } from "../lib/api";

const Grid = WidthProvider(Responsive);
const COLS = 12;

function sizeFor(type: string): { w: number; h: number } {
  if (type === "kpi") return { w: 3, h: 4 };
  if (type === "distribution") return { w: 4, h: 9 };
  if (type === "breakdown") return { w: 5, h: 9 };
  return { w: 8, h: 9 }; // trend / comparison
}

function buildLayout(cards: IntentCard[]): Layout[] {
  const layout: Layout[] = [];
  let x = 0;
  let y = 0;
  let rowH = 0;
  for (const c of cards) {
    const { w, h } = sizeFor(c.type);
    if (x + w > COLS) {
      x = 0;
      y += rowH;
      rowH = 0;
    }
    layout.push({ i: c.intent_id, x, y, w, h, minW: 2, minH: 3 });
    x += w;
    rowH = Math.max(rowH, h);
  }
  return layout;
}

export function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className={`panel h-56 animate-pulse ${i === 0 ? "md:col-span-2" : ""}`}
        />
      ))}
    </div>
  );
}

export default function DashboardGrid({
  cards,
  palette,
  animate,
  initialLayout,
  onLayoutChange,
}: {
  cards: IntentCard[];
  palette: Palette;
  animate: boolean;
  initialLayout?: Layout[];
  onLayoutChange?: (layout: Layout[]) => void;
}) {
  const layout = useMemo(
    () => (initialLayout && initialLayout.length ? initialLayout : buildLayout(cards)),
    [cards, initialLayout],
  );

  return (
    <Grid
      className="layout"
      layouts={{ lg: layout, md: layout }}
      breakpoints={{ lg: 1024, md: 768, sm: 0 }}
      cols={{ lg: COLS, md: COLS, sm: 4 }}
      rowHeight={30}
      margin={[16, 16]}
      isResizable
      isDraggable
      draggableHandle=".panel"
      compactType="vertical"
      onLayoutChange={(l) => onLayoutChange?.(l)}
    >
      {cards.map((card, i) => (
        <div key={card.intent_id}>
          <motion.div
            className="h-full"
            initial={animate ? { opacity: 0, y: 16 } : false}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: animate ? i * 0.08 : 0, ease: "easeOut" }}
          >
            <ChartCard card={card} palette={palette} />
          </motion.div>
        </div>
      ))}
    </Grid>
  );
}
