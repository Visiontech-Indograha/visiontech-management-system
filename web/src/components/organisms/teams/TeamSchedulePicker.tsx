import { useState } from "react";
import { useTeamsAvailability, type TeamAvailabilityItem } from "@/services/teamService";
import { AlertCircle, Calendar, Check, ChevronDown, Users } from "@/components/molecules/Glyphs";
import { ControlLabel } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { PlainAction } from "@/components/molecules/PlainAction";
import { TextBlock } from "@/components/molecules/TextBlock";

interface TeamSchedulePickerProps {
  value?: string | null;
  onChange: (teamId: string, team?: TeamAvailabilityItem) => void;
  workDate?: string;
  divisionId?: string | null;
  label?: string;
  required?: boolean;
  error?: string;
  className?: string;
}

export function TeamSchedulePicker({
  value,
  onChange,
  workDate,
  divisionId,
  label = "Pilih Tim Pelaksana",
  required = false,
  error,
  className = "",
}: TeamSchedulePickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { data: teams, isLoading, isError } = useTeamsAvailability(workDate, divisionId);

  const selectedTeam = teams?.find((t) => t.team_id === value);

  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      {label && (
        <ControlLabel className="text-xs font-semibold uppercase tracking-wider text-mist">
          <TextBlock className="text-xs font-semibold uppercase tracking-wider text-mist">
            {required ? `${label} *` : label}
          </TextBlock>
        </ControlLabel>
      )}

      {/* Trigger Button */}
      <div className="relative">
        <PlainAction
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className={`flex h-11 w-full items-center justify-between rounded-control border bg-surface px-3 py-2 text-left text-sm transition-all focus:outline-none focus:ring-2 focus:ring-primary ${
            error ? "border-danger ring-danger/20" : "border-line hover:border-mist"
          }`}
        >
          {selectedTeam ? (
            <div className="flex items-center gap-2 overflow-hidden">
              <div
                className={`h-2.5 w-2.5 shrink-0 rounded-full ${
                  selectedTeam.status === "AVAILABLE"
                    ? "bg-emerald-500"
                    : selectedTeam.status === "LEAVE"
                      ? "bg-amber-500"
                      : "bg-rose-500"
                }`}
              />
              <div className="truncate font-medium text-ink">
                <TextBlock className="font-medium text-ink">{selectedTeam.name}</TextBlock>
              </div>
              <div className="text-xs text-mist">
                <TextBlock className="text-xs text-mist">
                  {` (Ketua: ${selectedTeam.leader_name || "-"})`}
                </TextBlock>
              </div>
              <div className="ml-auto shrink-0">
                <TextBlock
                  className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                    selectedTeam.status === "AVAILABLE"
                      ? "bg-emerald-100 text-emerald-800"
                      : selectedTeam.status === "LEAVE"
                        ? "bg-amber-100 text-amber-800"
                        : "bg-rose-100 text-rose-800"
                  }`}
                >
                  {selectedTeam.status === "AVAILABLE"
                    ? "🟢 Siap (Free)"
                    : selectedTeam.status === "LEAVE"
                      ? "🟡 Cuti"
                      : `🔴 Sibuk (${selectedTeam.active_items_count} tugas)`}
                </TextBlock>
              </div>
            </div>
          ) : (
            <div className="text-mist">
              <TextBlock className="text-mist">
                {isLoading ? "Memuat ketersediaan tim..." : "Pilih tim berdasarkan ketersediaan jadwal..."}
              </TextBlock>
            </div>
          )}
          <ChevronDown size={16} className="shrink-0 text-mist" />
        </PlainAction>

        {/* Dropdown Menu with Live Schedule Peek */}
        {isOpen && (
          <div className="relative">
            <div
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
            />
            <div className="absolute left-0 top-full z-50 mt-1 max-h-72 w-full overflow-y-auto rounded-panel border border-line bg-surface p-1.5 shadow-card">
              <div className="flex items-center justify-between border-b border-line px-2 py-1.5 text-[11px] font-semibold text-mist">
                <div className="flex items-center gap-1.5">
                  <Calendar size={12} className="text-mist" />
                  <TextBlock className="text-[11px] text-mist">
                    {`Ketersediaan Tanggal: ${workDate || "Hari Ini"}`}
                  </TextBlock>
                </div>
                <div>
                  <TextBlock className="text-[11px] text-mist">
                    {`${teams?.length || 0} Tim`}
                  </TextBlock>
                </div>
              </div>

              {isLoading && (
                <div className="py-6 text-center">
                  <TextBlock className="text-xs text-mist">
                    Memeriksa jadwal dan ketersediaan tim...
                  </TextBlock>
                </div>
              )}

              {isError && (
                <div className="flex items-center justify-center gap-1 py-4 text-center">
                  <AlertCircle size={14} className="text-danger" />
                  <TextBlock className="text-xs text-danger">Gagal memuat status tim</TextBlock>
                </div>
              )}

              {teams?.length === 0 && !isLoading && (
                <div className="py-6 text-center">
                  <TextBlock className="text-xs text-mist">
                    Tidak ada tim aktif ditemukan di divisi ini.
                  </TextBlock>
                </div>
              )}

              <div className="mt-1 divide-y divide-subtle">
                {teams?.map((team) => {
                  const isSelected = team.team_id === value;
                  const isAvail = team.status === "AVAILABLE";
                  const isLeave = team.status === "LEAVE";

                  return (
                    <PlainAction
                      key={team.team_id}
                      type="button"
                      onClick={() => {
                        onChange(team.team_id, team);
                        setIsOpen(false);
                      }}
                      className={`group flex w-full items-start justify-between rounded-control p-2 text-left transition-colors ${
                        isSelected
                          ? "bg-subtle font-medium"
                          : "hover:bg-hover"
                      }`}
                    >
                      <div className="flex items-start gap-2.5">
                        <div
                          className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${
                            isAvail
                              ? "bg-emerald-500"
                              : isLeave
                                ? "bg-amber-500"
                                : "bg-rose-500"
                          }`}
                        />
                        <div>
                          <div className="flex items-center gap-1.5">
                            <TextBlock className="text-sm font-semibold text-ink">
                              {team.name}
                            </TextBlock>
                            {isSelected && <Check size={14} className="text-success" />}
                          </div>
                          <div className="mt-0.5 flex items-center gap-2">
                            <TextBlock className="text-xs text-mist">
                              {`Ketua: ${team.leader_name || "-"}`}
                            </TextBlock>
                            <TextBlock className="text-xs text-mist">•</TextBlock>
                            <div className="flex items-center gap-0.5">
                              <Users size={12} className="text-mist" />
                              <TextBlock className="text-xs text-mist">
                                {`${team.member_count} teknisi`}
                              </TextBlock>
                            </div>
                          </div>
                          {team.active_tasks && team.active_tasks.length > 0 && (
                            <div className="mt-1 max-w-[280px] truncate rounded border border-rose-200 bg-rose-50/80 px-1.5 py-0.5">
                              <TextBlock className="truncate text-[11px] text-rose-700">
                                {`Jadwal: ${team.active_tasks.join(", ")}`}
                              </TextBlock>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="shrink-0 text-right">
                        <TextBlock
                          className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                            isAvail
                              ? "border border-emerald-200 bg-emerald-50 text-emerald-700"
                              : isLeave
                                ? "border border-amber-200 bg-amber-50 text-amber-700"
                                : "border border-rose-200 bg-rose-50 text-rose-700"
                          }`}
                        >
                          {isAvail ? "Siap" : isLeave ? "Cuti" : "Ada Jadwal"}
                        </TextBlock>
                      </div>
                    </PlainAction>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>

      {error && <FormErrorText message={error} />}
    </div>
  );
}
