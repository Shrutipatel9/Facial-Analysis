import type { Metadata } from "next"

import { InsightsArticleLayout } from "@/components/insights/InsightsArticleLayout"

export const metadata: Metadata = {
  title: "The 11 Features We Analyze",
  description: "How FaceIQ's report is structured, and the reasoning behind a fixed 11-feature breakdown.",
}

export default function Page() {
  return (
    <InsightsArticleLayout title="The 11 Features We Analyze, and Why We Chose Them" category="Using FaceIQ">
      <p>
        Every FaceIQ report is organized around the same fixed set of 11 facial features: Hair, Eyebrows, Eyes,
        Nose, Cheeks, Jaw, Lips, Chin, Skin, Neck, and Ears. It&apos;s the same structure every time, for every
        report -- and that consistency is a deliberate design choice, not an incidental one.
      </p>

      <h2>Why a fixed structure, rather than something that varies</h2>
      <p>
        A facial analysis could, in principle, group things differently from person to person -- more detail where
        there&apos;s more to say, less where there isn&apos;t. We chose not to do that. Keeping the same 11
        features across every report means your report is comparable to itself over time, and it means we never
        quietly skip a feature because there was less to observe. If a feature genuinely has limited visible detail
        in your photos, the report says so directly rather than filling the space with padding.
      </p>
      <p>
        A couple of features that are sometimes treated as their own category elsewhere -- smile-related
        observations, for instance -- are folded into a closely related feature (Lips, in that case) rather than
        becoming a twelfth or thirteenth category. The goal was a set of features specific enough to be genuinely
        useful, without fragmenting into so many categories that the report becomes harder to read as a whole.
      </p>

      <h2>What each feature section actually covers</h2>
      <p>
        Every feature follows the same internal pattern: a detailed written analysis grounded in your own
        measurements and photos, what&apos;s already working well, and -- where relevant -- practical suggestions
        worth considering. Some features naturally split into a few sub-sections (Hair, for example, covers style,
        hair loss, and overall hair health separately), while others are covered under one heading. Either way, the
        depth is the same: specific, grounded observations, not generic filler.
      </p>

      <h2>Not every feature has a numeric measurement</h2>
      <p>
        Most of the 11 features are backed by real computer-vision measurements -- geometry extracted directly from
        your photos. A couple, like Hair and Neck, don&apos;t have a reliable geometric measurement behind them in
        the same way, so those sections rely on a careful visual read of your photos instead. We never invent a
        number to fill a gap -- if there&apos;s no real measurement, the report is built entirely from what&apos;s
        actually visible, at the same level of depth as every other section.
      </p>
    </InsightsArticleLayout>
  )
}
