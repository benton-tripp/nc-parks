import type { Park } from "../../types/park";
import ParkDetailContent from "./ParkDetailContent";

interface Props {
  park: Park;
  onClose: () => void;
}

/** Mobile-only bottom sheet wrapper around ParkDetailContent. */
export default function ParkDetail({ park, onClose }: Props) {
  return (
    <>
      {/* Mobile backdrop */}
      <div
        className="fixed inset-0 z-30 bg-black/40 md:hidden"
        onClick={onClose}
      />

      {/* Bottom sheet (mobile only) */}
      <div
        className="fixed inset-x-0 bottom-0 z-40 flex max-h-[70vh] flex-col rounded-t-2xl
                   bg-white shadow-2xl md:hidden"
      >
        {/* Drag handle */}
        <div className="flex justify-center py-2">
          <div className="h-1 w-8 rounded-full bg-gray-300" />
        </div>
        <div className="flex-1 overflow-y-auto px-4 pb-4">
          <ParkDetailContent park={park} onClose={onClose} />
        </div>
      </div>
    </>
  );
}
