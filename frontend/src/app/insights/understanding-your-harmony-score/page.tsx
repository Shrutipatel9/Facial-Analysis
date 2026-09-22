import type { Metadata } from "next"

import { InsightsArticleLayout } from "@/components/insights/InsightsArticleLayout"

export const metadata: Metadata = {
  title: "Understanding Your Harmony Score",
  description: "What the harmony score on your report actually measures, and what it deliberately isn't.",
}

export default function Page() {
  return (
    <InsightsArticleLayout title="Understanding Your Harmony Score" category="Using FaceIQ">
      <p>
        Every FaceIQ report includes an overall score alongside a per-feature breakdown across all 11 features we
        analyze. It&apos;s easy to read that number the way you&apos;d read a grade -- a single verdict on your
        face. That&apos;s not what it is, and it&apos;s worth being precise about what it actually represents.
      </p>

      <h2>It&apos;s a measurement comparison, not a beauty ranking</h2>
      <p>
        Each feature score comes from comparing your own computer-vision measurements -- ratios, angles, and
        proportions extracted from your photos -- against typical ranges for that feature. A high score means your
        measurements fall within a range that&apos;s commonly associated with balanced, harmonious proportions for
        that feature. It is not a statement about attractiveness in any absolute sense, and it&apos;s never meant to
        be read as one.
      </p>
      <p>
        The overall score is simply a summary across all 11 features, not a separate judgment layered on top. If you
        want to understand where it comes from, the per-feature breakdown is the real source -- the overall number
        is just a quick way to see the shape of the whole picture at a glance.
      </p>

      <h2>What moves the score, and what doesn&apos;t</h2>
      <p>
        A feature&apos;s score is grounded in what&apos;s actually measurable from your photos: things like facial
        thirds and fifths, symmetry between left and right, and proportional relationships between features. It
        does not factor in skin conditions that change day to day, temporary things like styling or makeup, or
        anything we can&apos;t reliably measure from a photo. If a feature genuinely isn&apos;t measurable from your
        photos -- an angle that doesn&apos;t show it clearly, for instance -- we say so explicitly rather than
        guessing at a number.
      </p>

      <h2>Why we show the finding, not just the number</h2>
      <p>
        Every score on your report is paired with a plain-language explanation of what&apos;s actually driving it.
        We do this deliberately: a number with no context invites exactly the kind of anxious over-interpretation
        we&apos;re trying to avoid. The finding tells you what the measurement means in practice; the number is
        there for people who want the underlying detail, not as the headline.
      </p>
      <p>
        If a section of your report reads as more clinical description than verdict, that&apos;s intentional. The
        goal of a FaceIQ report is to give you an accurate, grounded picture of your own face -- not to tell you
        how you should feel about it.
      </p>
    </InsightsArticleLayout>
  )
}
