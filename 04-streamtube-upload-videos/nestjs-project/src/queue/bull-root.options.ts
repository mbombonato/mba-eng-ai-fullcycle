import type { ConfigType } from '@nestjs/config';
import queueConfig from '../config/queue.config';

/** Shared BullMQ root options (API producer and worker consumer). */
export const bullRootAsyncOptions = {
  inject: [queueConfig.KEY],
  useFactory: (cfg: ConfigType<typeof queueConfig>) => ({
    connection: { host: cfg.host, port: cfg.port },
  }),
};
