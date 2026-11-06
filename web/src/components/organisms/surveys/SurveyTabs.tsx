import type { ReactNode } from "react";
import { TabsBlock, TabsBlockContent, TabsBlockList, TabsBlockTrigger } from "@/components/molecules/TabsBlock";

/** Tab detail survei. */
export function SurveyTabs({ points, map, preview, bom }: {
  points: ReactNode;
  map: ReactNode;
  preview: ReactNode;
  bom: ReactNode;
}) {
  return (
    <TabsBlock defaultValue="points">
      <TabsBlockList>
        <TabsBlockTrigger value="points">Titik dan foto</TabsBlockTrigger>
        <TabsBlockTrigger value="map">Peta layout</TabsBlockTrigger>
        <TabsBlockTrigger value="preview">Pratinjau laporan</TabsBlockTrigger>
        <TabsBlockTrigger value="bom">Daftar material</TabsBlockTrigger>
      </TabsBlockList>
      <TabsBlockContent value="points" className="mt-4">{points}</TabsBlockContent>
      <TabsBlockContent value="map" className="mt-4">{map}</TabsBlockContent>
      <TabsBlockContent value="preview" className="mt-4">{preview}</TabsBlockContent>
      <TabsBlockContent value="bom" className="mt-4">{bom}</TabsBlockContent>
    </TabsBlock>
  );
}
