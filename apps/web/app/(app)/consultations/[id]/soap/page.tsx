import { SOAPReviewForm } from "@/components/soap-review-form"

export default async function SOAPReviewPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  return <SOAPReviewForm consultationId={id} />
}
