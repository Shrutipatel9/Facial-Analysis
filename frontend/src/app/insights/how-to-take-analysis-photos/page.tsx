import type { Metadata } from "next"

import { InsightsArticleLayout } from "@/components/insights/InsightsArticleLayout"

export const metadata: Metadata = {
  title: "How to Take Photos for the Most Accurate Analysis",
  description: "The lighting, angle, and framing that actually affects measurement accuracy.",
}

export default function Page() {
  return (
    <InsightsArticleLayout
      title="How to Take Photos That Give You the Most Accurate Analysis"
      category="Using FaceIQ"
    >
      <p>
        FaceIQ&apos;s analysis is only as good as the photos it starts from. Every photo you upload is checked
        automatically before it&apos;s accepted, and a photo that fails one of those checks gets flagged with the
        specific reason -- so you can retake it rather than guess what went wrong. Here&apos;s what those checks
        are actually looking for, and how to get a clean pass on the first try.
      </p>

      <h2>The three angles</h2>
      <p>
        You&apos;ll upload three photos: front-facing, and a left and right three-quarter turn (roughly a 45°
        turn of your head to each side). Each angle captures different geometry -- the front photo is what most
        symmetry and proportion measurements are built from, while the side angles let us assess projection and
        contour that a front-facing photo alone can&apos;t show. Turning too far (toward a full profile) or not
        far enough both reduce how usable the angle is, so aim for a natural, roughly 45° turn rather than either
        extreme.
      </p>

      <h2>Lighting and exposure</h2>
      <p>
        Even, front-facing light is what actually matters -- a single strong side light creates shadows that can
        distort how measurements read, even though it might look flattering to the eye. Natural daylight facing a
        window works well. Avoid backlighting (a bright window or light behind you), which tends to leave your
        face underexposed even if the room looks well-lit overall.
      </p>

      <h2>Framing and resolution</h2>
      <p>
        Your whole face should be clearly in frame, with nothing cropped out and no filters or heavy retouching
        applied -- both distort the geometry the analysis depends on. Use a reasonably high-resolution photo; a
        modern phone camera is more than sufficient, but a heavily compressed or very low-resolution image can
        fail the check outright. A neutral expression works best, since an exaggerated expression shifts facial
        landmarks away from their resting position.
      </p>

      <h2>What else can cause a photo to be rejected</h2>
      <p>
        A few other things the automatic check looks for: exactly one face clearly visible (group photos or photos
        with someone else partially in frame won&apos;t pass), and minimal occlusion -- glasses, hats, or hair
        covering key parts of your face can obscure exactly the areas the analysis needs to see. None of these are
        arbitrary hurdles; each one maps directly to something that would otherwise make a measurement unreliable
        rather than just imprecise.
      </p>
    </InsightsArticleLayout>
  )
}
