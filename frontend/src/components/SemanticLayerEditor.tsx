import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  generateSemanticLayer,
  getSemanticLayer,
  listSemanticVersions,
  updateSemanticLayer,
} from "../lib/api";

/**
 * Minimal semantic-layer editor: generate, edit YAML, save new versions, and
 * browse version history. Intentionally plain — the real UI arrives in Phase 4.
 */
export default function SemanticLayerEditor({ projectId }: { projectId: string }) {
  const qc = useQueryClient();
  const [yaml, setYaml] = useState("");
  const [viewing, setViewing] = useState<number | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  const layer = useQuery({
    queryKey: ["semantic-layer", projectId, viewing],
    queryFn: () => getSemanticLayer(projectId, viewing),
    retry: false,
  });

  const versions = useQuery({
    queryKey: ["semantic-versions", projectId],
    queryFn: () => listSemanticVersions(projectId),
  });

  useEffect(() => {
    if (layer.data) setYaml(layer.data.yaml);
  }, [layer.data]);

  const refresh = () => {
    setViewing(undefined);
    setError(null);
    qc.invalidateQueries({ queryKey: ["semantic-layer", projectId] });
    qc.invalidateQueries({ queryKey: ["semantic-versions", projectId] });
  };

  const generate = useMutation({
    mutationFn: () => generateSemanticLayer(projectId),
    onSuccess: refresh,
    onError: (e: Error) => setError(e.message),
  });

  const save = useMutation({
    mutationFn: () => updateSemanticLayer(projectId, yaml),
    onSuccess: refresh,
    onError: (e: Error) => setError(e.message),
  });

  const hasLayer = layer.isSuccess;

  return (
    <div className="mt-4 rounded-lg border border-slate-700 p-4 text-sm">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-medium text-slate-300">Semantic layer</span>
        <div className="flex gap-2">
          <button
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
            className="rounded bg-slate-800 px-3 py-1 text-xs text-slate-200 hover:bg-slate-700 disabled:opacity-50"
          >
            {generate.isPending ? "Generating…" : hasLayer ? "Regenerate" : "Generate"}
          </button>
          <button
            onClick={() => save.mutate()}
            disabled={save.isPending || !yaml}
            className="rounded bg-accent px-3 py-1 text-xs font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {save.isPending ? "Saving…" : "Save new version"}
          </button>
        </div>
      </div>

      {!hasLayer && !layer.isLoading && (
        <p className="text-slate-400">No semantic layer yet — click Generate.</p>
      )}

      {error && <p className="mb-2 text-red-400">{error}</p>}

      {(hasLayer || yaml) && (
        <div className="grid gap-3 md:grid-cols-[1fr_160px]">
          <textarea
            value={yaml}
            onChange={(e) => setYaml(e.target.value)}
            spellCheck={false}
            className="h-72 w-full resize-y rounded border border-slate-700 bg-slate-950 p-3 font-mono text-xs text-slate-200"
          />
          <div>
            <div className="mb-1 text-xs font-medium text-slate-400">Versions</div>
            <ul className="space-y-1">
              {versions.data?.map((v) => (
                <li key={v.version}>
                  <button
                    onClick={() => setViewing(v.is_active ? undefined : v.version)}
                    className={`w-full rounded px-2 py-1 text-left text-xs ${
                      (viewing ?? layer.data?.version) === v.version
                        ? "bg-slate-700 text-white"
                        : "text-slate-300 hover:bg-slate-800"
                    }`}
                  >
                    v{v.version} {v.is_active ? "· active" : ""}
                    <span className="block text-[10px] text-slate-500">{v.created_by}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
