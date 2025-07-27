
export function formatBytes(bytes: number): string {
    const gb = bytes / (1024 ** 3);
    const mb = bytes / (1024 ** 2);

    if (gb >= 1) return `${gb.toFixed(2)} GB`;
    if (mb >= 1) return `${mb.toFixed(2)} MB`;
    return `${bytes} B`;
}