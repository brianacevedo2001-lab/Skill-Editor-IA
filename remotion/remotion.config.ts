import { Config } from "@remotion/cli/config";

// Los medios de cada vídeo y los recursos compartidos viven en ../videos
// (videos/<id>/… y videos/_shared/…).
Config.setPublicDir("../videos");
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
