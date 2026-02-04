export default function FollowUpChips({ followUps = [], onClick }) {
  if (!Array.isArray(followUps) || followUps.length === 0) return null;

  return (
    <div className="followups">
      {followUps.map((f) => (
        <button
          key={f}
          type="button"
          className="chip"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => onClick?.(f)}
        >
          {f}
        </button>
      ))}
    </div>
  );
}
