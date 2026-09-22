import type { Metadata } from "next"

import { InsightsArticleLayout } from "@/components/insights/InsightsArticleLayout"

export const metadata: Metadata = {
  title: "Facial Symmetry and Proportion, Explained",
  description: "What symmetry and proportion actually mean in facial aesthetics, beyond the buzzwords.",
}

export default function Page() {
  return (
    <InsightsArticleLayout title="Facial Symmetry and Proportion, Explained" category="Facial Aesthetics Concepts">
      <p>
        &quot;Symmetry&quot; and &quot;proportion&quot; get used loosely in everyday conversation about faces, often
        as vague stand-ins for &quot;attractive.&quot; They&apos;re actually specific, measurable concepts, and
        understanding what they really mean makes it much easier to read any facial analysis -- including your
        own -- without over-interpreting it.
      </p>

      <h2>Symmetry: comparing left and right</h2>
      <p>
        Facial symmetry refers to how closely the left and right halves of your face mirror each other --
        comparing the position, size, and alignment of paired features like your eyes, eyebrows, and the corners of
        your mouth. No face is perfectly symmetrical; genuine, close-to-perfect symmetry is actually rare and can
        even look slightly uncanny in a photo. A completely symmetrical face isn&apos;t the goal or the norm --
        it&apos;s simply one measurable property among several.
      </p>
      <p>
        A small degree of asymmetry is normal and expected. What a symmetry measurement is actually useful for is
        identifying a genuinely notable asymmetry worth being aware of -- not chasing an unrealistic ideal of
        perfect mirror-image balance.
      </p>

      <h2>Proportion: how features relate to each other</h2>
      <p>
        Proportion is about relationships, not absolute size. It&apos;s not whether your nose is &quot;big&quot; or
        &quot;small&quot; in isolation -- it&apos;s how its size and position relate to the rest of your face: the
        distance between your eyes relative to eye width, the vertical spacing between your hairline, brows, nose,
        and chin, that kind of thing. You&apos;ve probably heard of the idea of dividing a face into horizontal
        thirds or vertical fifths -- these are classic reference frameworks for describing proportional balance,
        not rules a face needs to satisfy exactly.
      </p>
      <p>
        Like symmetry, proportion measurements are descriptive, not prescriptive. They tell you how your own
        features relate to each other and to typical ranges -- they&apos;re a way of describing a face precisely,
        not a scale of how a face &quot;should&quot; look.
      </p>

      <h2>Why both matter for reading your own report</h2>
      <p>
        When FaceIQ&apos;s report discusses symmetry or proportion for a specific feature, it&apos;s describing one
        measurable property of your face -- grounded in real geometry from your own photos -- not delivering a
        verdict. Both concepts are genuinely useful for understanding your own face in detail. Neither one is the
        whole picture on its own.
      </p>
    </InsightsArticleLayout>
  )
}
