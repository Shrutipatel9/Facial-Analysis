import type { Metadata } from "next"

import { InsightsArticleLayout } from "@/components/insights/InsightsArticleLayout"

export const metadata: Metadata = {
  title: "What Is Facial Prototypicality?",
  description: "A real perception-research concept, explained without the judgment the name might suggest.",
}

export default function Page() {
  return (
    <InsightsArticleLayout
      title="What Is Facial Prototypicality (and Why It's Not About Looking 'Normal')"
      category="Facial Aesthetics Concepts"
    >
      <p>
        Prototypicality is one of the less intuitive terms you might encounter in a facial analysis, and the name
        alone can sound like it&apos;s asking whether your face is &quot;normal.&quot; It isn&apos;t, and it&apos;s
        worth explaining what the term actually means before it&apos;s misread that way.
      </p>

      <h2>What it actually measures</h2>
      <p>
        In facial-perception research, prototypicality describes how closely a face&apos;s proportions sit near the
        statistical average of a larger reference set of faces -- not a judgment of whether those proportions are
        good or unusual, just a measure of distance from an average. It&apos;s sometimes discussed alongside
        research on the &quot;averageness effect&quot;: the well-documented finding that faces closer to an
        averaged composite tend to be perceived as familiar and harmonious, independent of any single distinctive
        feature.
      </p>
      <p>
        That research finding is genuinely interesting, but it doesn&apos;t mean average is somehow superior, and
        it definitely doesn&apos;t mean distinctive features are a flaw. Plenty of features widely considered
        striking or memorable are, by definition, further from average -- prototypicality is one descriptive lens
        among several, not a ranking of what&apos;s best.
      </p>

      <h2>Why we include it, and how to read it</h2>
      <p>
        We include a prototypicality measurement because it&apos;s a real, established concept in how faces are
        studied and perceived -- leaving it out would mean leaving out a genuine part of the picture. But it&apos;s
        one data point among the full set your report covers, not a headline verdict. A face that measures further
        from average isn&apos;t a face with a problem; it&apos;s simply a face with more distinctive proportions in
        one or more areas.
      </p>
      <p>
        As with every other measurement on your report, the goal is description, not judgment. Prototypicality
        tells you something real and specific about your own facial geometry -- what you do with that information,
        if anything, is entirely up to you.
      </p>
    </InsightsArticleLayout>
  )
}
