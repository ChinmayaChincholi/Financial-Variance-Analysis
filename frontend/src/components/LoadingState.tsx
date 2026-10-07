interface LoadingStateProps {
  message: string;
}

export function LoadingState({
  message,
}: LoadingStateProps) {
  return (
    <div className="loading-state">
      <div className="spinner" />

      <h2>Processing dataset</h2>

      <p>{message}</p>
    </div>
  );
}