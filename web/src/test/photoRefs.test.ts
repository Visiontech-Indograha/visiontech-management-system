import { describe, expect, it } from "vitest";
import { photoRefs } from "@/lib/photoRefs";

describe("photoRefs", () => {
  it("menormalkan objek dan string id lama, mengabaikan data rusak", () => {
    expect(photoRefs([{ file_id: "a", requirement_id: "r" }, "b", null, 3, { file_id: "" }, ""])).toEqual([
      { file_id: "a", requirement_id: "r" },
      { file_id: "b" },
    ]);
    expect(photoRefs(null)).toEqual([]);
    expect(photoRefs({})).toEqual([]);
  });
});
