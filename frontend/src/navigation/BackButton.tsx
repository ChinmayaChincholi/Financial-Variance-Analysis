import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface BackButtonProps {
  fallback?: string;
}

export function BackButton({
  fallback = "/",
}: BackButtonProps) {
  const navigate = useNavigate();

  function handleBack() {
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate(fallback);
    }
  }

  return (
    <button
      type="button"
      className="back-button"
      onClick={handleBack}
      aria-label="Go back"
    >
      <ArrowLeft size={20} />
    </button>
  );
}