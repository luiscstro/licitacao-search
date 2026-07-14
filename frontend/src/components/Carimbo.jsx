export default function Carimbo({ cor = "neutro", children }) {
  return <span className={`carimbo ${cor}`}>{children}</span>;
}