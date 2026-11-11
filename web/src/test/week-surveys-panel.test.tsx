import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { WeekSurveysPanel } from "@/components/organisms/work-plans/WeekSurveysPanel";
import type { ScheduledSurvey } from "@/services/dailyPlanService";

const survey = (over: Partial<ScheduledSurvey> = {}): ScheduledSurvey => ({
  survey_id: "s1", work_order_id: "w1", wo_number: "WO-001", title: "Survei CCTV gudang",
  client_name: "PT Uji", site_name: "Gudang Duri", survey_date: "2026-12-01", survey_status: "DRAFT",
  surveyor_team_id: "t1", surveyor_team_name: "Tim Riau", filled_points: 0,
  ...over,
});

describe("Survei dijadwalkan di Jadwal harian (B-05)", () => {
  it("menampilkan survei yang ditugaskan beserta tim dan lokasinya", () => {
    render(<WeekSurveysPanel surveys={[survey()]} />);
    expect(screen.getByText("Survei dijadwalkan minggu ini (1)")).toBeInTheDocument();
    expect(screen.getByText(/WO-001 · Survei CCTV gudang/)).toBeInTheDocument();
    expect(screen.getByText(/Tim Tim Riau · PT Uji · Gudang Duri/)).toBeInTheDocument();
  });

  it("tidak menampilkan apa pun bila tidak ada survei", () => {
    const { container } = render(<WeekSurveysPanel surveys={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
