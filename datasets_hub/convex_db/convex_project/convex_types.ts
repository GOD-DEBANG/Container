export interface GenericDatabaseWriter {
  insert(table: string, value: Record<string, any>): Promise<string>;
}

export interface GenericDatabaseReader {
  query(table: string): {
    order(dir: "asc" | "desc"): {
      take(n: number): Promise<any[]>;
    };
  };
}

export interface MutationCtx {
  db: GenericDatabaseWriter;
}

export interface QueryCtx {
  db: GenericDatabaseReader;
}

export interface Validator<T = any> {
  type: string;
}

export const v = {
  string: (): Validator<string> => ({ type: "string" }),
  number: (): Validator<number> => ({ type: "number" }),
  boolean: (): Validator<boolean> => ({ type: "boolean" }),
  any: (): Validator<any> => ({ type: "any" }),
  array: (val: any): Validator<any[]> => ({ type: "array" }),
  optional: (val: any): Validator<any | undefined> => ({ type: "optional" }),
};

export function defineSchema(tables: Record<string, any>) {
  return tables;
}

export function defineTable(fields: Record<string, any>) {
  return {
    fields,
    index(name: string, fields: string[]) {
      return this;
    },
  };
}

export function mutation(config: {
  args: Record<string, any>;
  handler: (ctx: MutationCtx, args: any) => Promise<any>;
}) {
  return config;
}

export function query(config: {
  args: Record<string, any>;
  handler: (ctx: QueryCtx, args: any) => Promise<any>;
}) {
  return config;
}
