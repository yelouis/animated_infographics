import fs from "node:fs";
import path from "node:path";
import { bundle } from "@remotion/bundler";
import {
  openBrowser,
  renderMedia,
  renderStill,
  selectComposition,
  type BrowserLog,
} from "@remotion/renderer";
import Ajv from "ajv";
import schema from "../../schema/timeline.schema.json";

interface OverflowEntry {
  scene_id: string;
  template: string;
  slot: string;
}

interface FrameEntry {
  scene_id: string;
  frame: number;
  out: string;
}

function parseArgs(args: string[]) {
  const mode = args[0];
  const options: Record<string, string | boolean> = {};

  for (let i = 1; i < args.length; i++) {
    const arg = args[i];
    if (arg.startsWith("--")) {
      const key = arg.slice(2);
      const nextArg = args[i + 1];
      if (nextArg && !nextArg.startsWith("--")) {
        options[key] = nextArg;
        i++;
      } else {
        options[key] = true;
      }
    }
  }

  return { mode, options };
}

function assemblePublicDir(jobDir: string): string {
  const renderPublicDir = path.join(jobDir, "render_public");
  fs.rmSync(renderPublicDir, { recursive: true, force: true });
  fs.mkdirSync(renderPublicDir, { recursive: true });

  // 1. Copy renderer/public/*
  const rendererPublic = path.resolve(__dirname, "../public");
  if (fs.existsSync(rendererPublic)) {
    fs.cpSync(rendererPublic, renderPublicDir, { recursive: true });
  }

  // 2. Copy job/ subtree (audio/ and assets/images/)
  const jobSubtree = path.join(renderPublicDir, "job");
  fs.mkdirSync(jobSubtree, { recursive: true });

  const jobAudio = path.join(jobDir, "audio");
  if (fs.existsSync(jobAudio)) {
    fs.cpSync(jobAudio, path.join(jobSubtree, "audio"), { recursive: true });
  }

  const jobImages = path.join(jobDir, "assets/images");
  if (fs.existsSync(jobImages)) {
    fs.cpSync(jobImages, path.join(jobSubtree, "assets/images"), {
      recursive: true,
    });
  }

  // 3. Copy fixtures if available (for test beds / smoke runs)
  const repoFixtures = path.resolve(__dirname, "../../fixtures");
  if (fs.existsSync(repoFixtures)) {
    fs.cpSync(repoFixtures, path.join(renderPublicDir, "fixtures"), {
      recursive: true,
    });
  }

  return renderPublicDir;
}

async function main() {
  const { mode, options } = parseArgs(process.argv.slice(2));

  if (!mode || !["stills", "media", "gallery"].includes(mode)) {
    console.error(
      "Usage: npx tsx scripts/render.ts <stills|media|gallery> --job <job_dir> [options]"
    );
    process.exit(1);
  }

  const jobDir = path.resolve(
    String(options.job || (mode === "gallery" ? "." : ""))
  );
  if (!jobDir) {
    console.error("Missing required --job argument");
    process.exit(1);
  }

  const logsDir = path.join(jobDir, "logs");
  fs.mkdirSync(logsDir, { recursive: true });
  const browserLogPath = path.join(logsDir, "render_browser.log");
  const overflowJsonPath = path.join(logsDir, "overflow.json");

  const overflowMap = new Map<string, OverflowEntry>();

  const onBrowserLog = (log: BrowserLog) => {
    fs.appendFileSync(browserLogPath, `[${log.type}] ${log.text}\n`);
    const match = log.text.match(
      /^OVERFLOW\s+scene=(\S+)\s+template=(\S+)\s+slot=(\S+)/
    );
    if (match) {
      const entry: OverflowEntry = {
        scene_id: match[1],
        template: match[2],
        slot: match[3],
      };
      const key = `${entry.scene_id}::${entry.template}::${entry.slot}`;
      overflowMap.set(key, entry);
    }
  };

  // Validate timeline if in stills or media mode
  let timeline: Record<string, unknown> | null = null;
  if (mode === "stills" || mode === "media") {
    const timelinePath = options.timeline
      ? path.resolve(String(options.timeline))
      : path.join(jobDir, "timeline.json");

    if (!fs.existsSync(timelinePath)) {
      console.error(`Timeline file not found: ${timelinePath}`);
      process.exit(2);
    }

    try {
      timeline = JSON.parse(fs.readFileSync(timelinePath, "utf8"));
    } catch (err) {
      console.error("Failed to parse timeline JSON:", err);
      process.exit(2);
    }

    const ajv = new Ajv({ allErrors: true, strict: false });
    ajv.addKeyword({ keyword: "discriminator" });
    const validate = ajv.compile(schema);
    const valid = validate(timeline);
    if (!valid) {
      console.error("Timeline validation failed:", validate.errors?.slice(0, 10));
      process.exit(2);
    }

    if (options["sync-probe"] && timeline) {
      const debug = (timeline.debug || {}) as Record<string, unknown>;
      timeline.debug = { ...debug, sync_probe: true };
    }
  }

  // Assemble publicDir
  const publicDir = assemblePublicDir(jobDir);

  // Bundle Remotion project
  console.log("Bundling Remotion project...");
  const entryPoint = path.resolve(__dirname, "../src/index.ts");
  let bundleLocation: string;
  try {
    bundleLocation = await bundle({
      entryPoint,
      publicDir,
    });
  } catch (bundleErr) {
    console.error("Bundling failed:", bundleErr);
    process.exit(1);
  }

  // Open single browser instance
  console.log("Launching headless browser...");
  let browser;
  try {
    browser = await openBrowser("chrome");
  } catch (err) {
    console.error("Failed to open browser:", err);
    process.exit(1);
  }

  try {
    if (mode === "media") {
      const outPath = options.out
        ? path.resolve(String(options.out))
        : path.join(jobDir, "out.mp4");
      fs.mkdirSync(path.dirname(outPath), { recursive: true });

      const scale = options.scale !== undefined ? Number(options.scale) : 1.0;
      const crf = options.crf !== undefined ? Number(options.crf) : 18;

      console.log(`Selecting Story composition...`);
      const composition = await selectComposition({
        serveUrl: bundleLocation,
        id: "Story",
        inputProps: timeline as Record<string, unknown>,
        puppeteerInstance: browser,
      });

      console.log(
        `Rendering media to ${outPath} (scale=${scale}, crf=${crf})...`
      );
      await renderMedia({
        composition,
        serveUrl: bundleLocation,
        outputLocation: outPath,
        inputProps: timeline as Record<string, unknown>,
        puppeteerInstance: browser,
        codec: "h264",
        crf,
        pixelFormat: "yuv420p",
        imageFormat: "jpeg",
        jpegQuality: 90,
        audioCodec: "aac",
        audioBitrate: "192k",
        scale,
        onBrowserLog,
        overwrite: true,
        ffmpegOverride: ({ type, args }) => {
          if (type === "stitcher") {
            const newArgs = [...args];
            const outIndex = newArgs.length - 1;
            newArgs.splice(outIndex, 0, "-shortest");
            return newArgs;
          }
          return args;
        },
        onStart: (data) => {
          console.log(`Render started with concurrency=${data.resolvedConcurrency}`);
        },
      });

      console.log(`Render complete: ${outPath}`);
    } else if (mode === "stills") {
      const framesFile = path.resolve(String(options.frames));
      if (!fs.existsSync(framesFile)) {
        console.error(`Frames file not found: ${framesFile}`);
        process.exit(1);
      }

      const frames: FrameEntry[] = JSON.parse(
        fs.readFileSync(framesFile, "utf8")
      );
      const scale = options.scale !== undefined ? Number(options.scale) : 0.5;

      const composition = await selectComposition({
        serveUrl: bundleLocation,
        id: "Story",
        inputProps: timeline as Record<string, unknown>,
        puppeteerInstance: browser,
      });

      for (const entry of frames) {
        const outPath = path.isAbsolute(entry.out)
          ? entry.out
          : path.join(jobDir, entry.out);
        fs.mkdirSync(path.dirname(outPath), { recursive: true });

        console.log(
          `Rendering still scene=${entry.scene_id} frame=${entry.frame} -> ${outPath}`
        );
        await renderStill({
          composition,
          serveUrl: bundleLocation,
          output: outPath,
          frame: entry.frame,
          inputProps: timeline as Record<string, unknown>,
          puppeteerInstance: browser,
          scale,
          imageFormat: "png",
          onBrowserLog,
          overwrite: true,
        });
      }
    } else if (mode === "gallery") {
      const outDir = path.resolve(String(options["out-dir"] || "artifacts/gallery"));
      fs.mkdirSync(outDir, { recursive: true });

      const templateToRender = options.template
        ? [String(options.template)]
        : ["kinetic_quote"];
      const variants: ("min" | "typical" | "max")[] = options.variant
        ? [options.variant as "min" | "typical" | "max"]
        : ["min", "typical", "max"];

      for (const tmpl of templateToRender) {
        for (const variant of variants) {
          const inputProps = { template: tmpl, variant };
          const composition = await selectComposition({
            serveUrl: bundleLocation,
            id: "Gallery",
            inputProps,
            puppeteerInstance: browser,
          });

          const outPath = path.join(outDir, `${tmpl}__${variant}.png`);
          console.log(`Rendering gallery still: ${tmpl}__${variant} -> ${outPath}`);
          await renderStill({
            composition,
            serveUrl: bundleLocation,
            output: outPath,
            frame: 60, // Hold frame
            inputProps,
            puppeteerInstance: browser,
            scale: options.scale !== undefined ? Number(options.scale) : 1.0,
            imageFormat: "png",
            onBrowserLog,
            overwrite: true,
          });
        }
      }
    }
  } catch (renderErr: unknown) {
    const errMsg = renderErr instanceof Error ? renderErr.message : String(renderErr);
    if (errMsg.includes("Timeline failed schema validation")) {
      console.error(errMsg);
      process.exit(2);
    }
    console.error("Rendering error:", renderErr);
    process.exit(1);
  } finally {
    await browser.close({ silent: false });

    // Write overflow.json
    const overflows = Array.from(overflowMap.values());
    fs.writeFileSync(overflowJsonPath, JSON.stringify(overflows, null, 2));

    if (mode === "gallery" && overflows.length > 0) {
      console.error(
        `Overflow detected in gallery mode (${overflows.length} overflows):`,
        overflows
      );
      process.exit(6);
    }
  }

  process.exit(0);
}

main().catch((err) => {
  console.error("Unhandled error:", err);
  process.exit(1);
});
