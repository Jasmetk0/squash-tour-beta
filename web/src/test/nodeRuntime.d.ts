declare module 'fs' {
  export function readFileSync(path: string, encoding: string): string
}

declare module 'path' {
  export function resolve(...paths: string[]): string
}

declare const process: {
  cwd: () => string
}
