import type { Metadata } from "next";
import StudioContent from "@/components/pages/StudioContent";

export const metadata: Metadata = { title: "Studio" };

export default function Page() {
  return <StudioContent />;
}
