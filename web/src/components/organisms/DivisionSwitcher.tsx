import { useSession } from "@/stores/sessionStore";
import { Building2, Check, ChevronDown } from "@/components/molecules/Glyphs";
import { Menu, MenuContent, MenuItem, MenuLabel, MenuSeparator, MenuTrigger } from "@/components/molecules/Menu";
import { TextBlock } from "@/components/molecules/TextBlock";

export function DivisionSwitcher() {
  const { me, activeDivisionId, setActiveDivisionId } = useSession();

  const managedDivisions = me?.managed_divisions || [];

  if (managedDivisions.length <= 1) {
    if (managedDivisions.length === 1) {
      return (
        <div className="flex items-center gap-1.5 rounded-control bg-subtle px-2.5 py-1 text-xs font-semibold text-ink">
          <Building2 size={14} className="text-mist" />
          <TextBlock className="text-xs font-semibold text-ink">{managedDivisions[0].name}</TextBlock>
        </div>
      );
    }
    return null;
  }

  const activeDivision = managedDivisions.find((d) => d.division_id === activeDivisionId);

  return (
    <div className="relative">
      <Menu>
        <MenuTrigger className="flex items-center gap-2 rounded-control border border-line bg-surface px-3 py-1.5 text-xs font-semibold text-ink shadow-sm transition hover:bg-hover focus:outline-none focus:ring-2 focus:ring-primary">
          <Building2 size={14} className="text-mist" />
          <div className="max-w-[140px] truncate text-left">
            <TextBlock className="text-xs font-semibold text-ink">
              {activeDivision ? activeDivision.name : "Semua Divisi"}
            </TextBlock>
          </div>
          <ChevronDown size={14} className="text-mist" />
        </MenuTrigger>
        <MenuContent align="start" className="w-56 p-1">
          <MenuLabel className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-mist">
            <TextBlock className="text-[10px] font-bold uppercase tracking-wider text-mist">
              {`Ganti Divisi Aktif (${managedDivisions.length})`}
            </TextBlock>
          </MenuLabel>
          <MenuItem
            onClick={() => setActiveDivisionId(null)}
            className="flex items-center justify-between text-xs"
          >
            <TextBlock className="text-xs">Semua Divisi</TextBlock>
            {activeDivisionId === null && <Check size={14} className="text-success" />}
          </MenuItem>
          <MenuSeparator />
          {managedDivisions.map((div) => {
            const isSelected = div.division_id === activeDivisionId;
            return (
              <MenuItem
                key={div.division_id}
                onClick={() => setActiveDivisionId(div.division_id)}
                className="flex items-center justify-between text-xs"
              >
                <div className="max-w-[170px] truncate">
                  <TextBlock className="text-xs">{div.name}</TextBlock>
                </div>
                {isSelected && <Check size={14} className="text-success" />}
              </MenuItem>
            );
          })}
        </MenuContent>
      </Menu>
    </div>
  );
}
