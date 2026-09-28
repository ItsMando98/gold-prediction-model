function Bar({ w, h = "1rem", mb = "0" }: { w: string; h?: string; mb?: string }) {
  return <div className="skeleton" style={{ width: w, height: h, marginBottom: mb }} />;
}

export default function Loading() {
  return (
    <>
      <div className="card hero-card">
        <Bar w="180px" h="3.25rem" mb="0.75rem" />
        <Bar w="100%" h="10px" mb="0.5rem" />
        <Bar w="60%" h="0.8rem" />
      </div>
      <div className="grid grid-stats" style={{ marginBottom: "1.25rem" }}>
        {[0, 1, 2, 3].map((i) => (
          <div className="stat-tile" key={i}>
            <Bar w="60%" h="0.7rem" mb="0.5rem" />
            <Bar w="80%" h="1.35rem" />
          </div>
        ))}
      </div>
      <div className="card">
        <Bar w="120px" h="0.8rem" mb="1rem" />
        <Bar w="100%" h="160px" />
      </div>
    </>
  );
}
