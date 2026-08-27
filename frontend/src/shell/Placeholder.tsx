/**
 * A view or tab that is on the rebuild list and not built yet.
 *
 * One component for all of them on purpose. Adding item 9 should be *replacing*
 * this in one place, not inventing a slot — and until then every unbuilt
 * surface reads as deliberately pending rather than as something that failed to
 * load. The item number is shown because the rebuild list is the shared
 * vocabulary for what is missing.
 */
export default function Placeholder({
  title,
  item,
  children,
}: {
  title: string;
  /** Rebuild-list item number, from streamlit_inventory.md §6. */
  item: number;
  /** One sentence on what will live here, so the slot is legible empty. */
  children: React.ReactNode;
}) {
  return (
    <section className="placeholder" role="status">
      <h2>{title}</h2>
      <p className="placeholder__badge">Not built yet — rebuild-list item {item}</p>
      <p>{children}</p>
    </section>
  );
}
