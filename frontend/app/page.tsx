import type { Metadata } from "next";
import VoicesContent from "@/components/pages/VoicesContent";

export const metadata: Metadata = { title: "Voices" };

export default function Page() {
  return <VoicesContent />;
}
