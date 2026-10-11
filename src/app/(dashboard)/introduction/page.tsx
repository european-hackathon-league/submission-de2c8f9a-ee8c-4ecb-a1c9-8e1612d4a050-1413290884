import { ActorLegend, PipelineGraph } from "@/components/introduction/pipeline-graph";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function IntroductionPage() {
  return (
    <>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Introduction</h1>
        <p className="text-sm text-muted-foreground">How an analysis is made.</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>How it works</CardTitle>
          <CardDescription className="flex flex-col gap-2">
            From one car and region to traceable requirements. Code computes every number and checks
            every LLM step; the LLM reads text and judges; the PM decides.
            <ActorLegend />
          </CardDescription>
        </CardHeader>
        <CardContent>
          <PipelineGraph />
        </CardContent>
      </Card>
    </>
  );
}
