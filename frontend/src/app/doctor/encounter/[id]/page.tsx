// frontend/src/app/doctor/encounter/[id]/page.tsx
import { redirect } from 'next/navigation';
import { use } from 'react';

export default function EncounterIdRootPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  redirect(`/doctor/encounter/${resolvedParams.id}/scribe`);
}
