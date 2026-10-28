import {
  useRef,
  useState,
  useImperativeHandle,
  forwardRef,
  type PointerEvent,
} from "react";
import { Canvas } from "@/components/atoms/Canvas";
import { Text } from "@/components/atoms/Text";
import { Button } from "@/components/atoms/Button";
import { Eraser, PenTool } from "@/components/atoms/Icon";

export interface SignaturePadHandle {
  getSignatureDataUrl: () => string | null;
  clear: () => void;
  hasSignature: boolean;
}

interface SignaturePadProps {
  label?: string;
  width?: number;
  height?: number;
  onChange?: (hasSignature: boolean) => void;
}

export const SignaturePad = forwardRef<SignaturePadHandle, SignaturePadProps>(
  function SignaturePad(
    {
      label = "Bubuhkan Tanda Tangan Digital",
      width = 460,
      height = 180,
      onChange,
    },
    ref
  ) {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const [isDrawing, setIsDrawing] = useState(false);
    const [hasSignature, setHasSignature] = useState(false);

    const getCanvasCoordinates = (e: PointerEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return { x: 0, y: 0 };
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      return {
        x: (e.clientX - rect.left) * scaleX,
        y: (e.clientY - rect.top) * scaleY,
      };
    };

    const handlePointerDown = (e: PointerEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      canvas.setPointerCapture(e.pointerId);
      setIsDrawing(true);
      if (!hasSignature) {
        setHasSignature(true);
        onChange?.(true);
      }

      const { x, y } = getCanvasCoordinates(e);
      ctx.strokeStyle = "#0f172a";
      ctx.lineWidth = 2.5;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.beginPath();
      ctx.moveTo(x, y);
    };

    const handlePointerMove = (e: PointerEvent<HTMLCanvasElement>) => {
      if (!isDrawing) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const { x, y } = getCanvasCoordinates(e);
      ctx.lineTo(x, y);
      ctx.stroke();
    };

    const handlePointerUp = (e: PointerEvent<HTMLCanvasElement>) => {
      if (!isDrawing) return;
      const canvas = canvasRef.current;
      if (canvas) {
        try {
          canvas.releasePointerCapture(e.pointerId);
        } catch {
          // pointer capture release fallback
        }
      }
      setIsDrawing(false);
    };

    const clearCanvas = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
      setHasSignature(false);
      onChange?.(false);
    };

    useImperativeHandle(ref, () => ({
      getSignatureDataUrl: () => {
        if (!hasSignature || !canvasRef.current) return null;
        return canvasRef.current.toDataURL("image/png");
      },
      clear: clearCanvas,
      hasSignature,
    }));

    return (
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-1.5 font-medium text-ink">
            <PenTool className="h-3.5 w-3.5 text-primary" />
            <Text as="span">{label}</Text>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={clearCanvas}
            className="h-7 px-2 text-xs text-mist hover:text-ink"
          >
            <Eraser className="mr-1 h-3.5 w-3.5" />
            <Text as="span">Bersihkan</Text>
          </Button>
        </div>

        <div className="relative rounded-control border-2 border-dashed border-line bg-white dark:bg-slate-900">
          <Canvas
            ref={canvasRef}
            width={width}
            height={height}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerCancel={handlePointerUp}
            className="w-full touch-none cursor-crosshair rounded-control"
          />
          {!hasSignature && (
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <Text className="text-xs text-slate-400 select-none">
                Sentuh atau seret kursor mouse di sini untuk tanda tangan
              </Text>
            </div>
          )}
        </div>
      </div>
    );
  }
);
