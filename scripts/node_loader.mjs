// Resolve Codex-provided packages without copying or hard-coding its runtime.
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
export async function resolve(specifier, context, nextResolve) {
  if (specifier === '@oai/artifact-tool') {
    const directory = process.env.LAB_RD_NODE_MODULES;
    if (!directory) throw new Error('Supply --node-modules from the Codex dependency loader');
    const require = createRequire(path.join(directory, '_lab_rd_resolve.cjs'));
    return {url: pathToFileURL(require.resolve(specifier)).href, shortCircuit: true};
  }
  return nextResolve(specifier, context);
}
