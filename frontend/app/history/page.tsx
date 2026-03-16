import type { Metadata } from "next";
import HistoryContent from "@/components/pages/HistoryContent";

export const metadata: Metadata = { title: "History" };

export default function Page() {
  return <HistoryContent />;
}
