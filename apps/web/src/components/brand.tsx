import Link from "next/link";

import styles from "./brand.module.css";

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link className={styles.brand} href="/" aria-label="VeriFlow AI home">
      <span className={styles.mark}>V</span>
      {!compact && <span>VeriFlow AI</span>}
    </Link>
  );
}
