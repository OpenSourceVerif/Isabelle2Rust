"""Kernel-v2 batch drivers. Algorithm sources remain unchanged.

Wire: B <count>, input line, expected output line. Responses contain elapsed
nanoseconds and checked result count. Every result is encoded/checked after time.
"""
import re

RAW_CLOCK = r'''#include <stdint.h>
#include <time.h>
uint64_t i2r_clock_ns(void) {
 struct timespec t;
 #ifdef CLOCK_MONOTONIC_RAW
 const clockid_t id=CLOCK_MONOTONIC_RAW;
 #else
 const clockid_t id=CLOCK_MONOTONIC;
 #endif
 if(clock_gettime(id,&t)!=0) __builtin_trap();
 return (uint64_t)t.tv_sec*1000000000ULL+(uint64_t)t.tv_nsec;
}
'''
OCAML_CLOCK = RAW_CLOCK + r'''
#include <caml/mlvalues.h>
#include <caml/alloc.h>
CAMLprim value i2r_raw_now(value unit) { return caml_copy_int64(i2r_clock_ns()); }
'''


def rust(source):
    if 'fn batch_v2_main' in source:return source
    wire=re.search(r'let values:\s*Vec<([^>]+)>',source)[1]
    prepare=re.search(r'let prepared\s*=\s*std::hint::black_box\(([^\n]+)\);',source)[1]
    run=re.search(r'let result\s*=\s*std::hint::black_box\(([^\n]+)\);',source)[1]
    encode=re.search(r'((?:benchmark|kernel)_encode\(&?result\))',source)[1]
    reference='isabelle_exported' in source
    convert='let input=values.iter().rev().fold(List::Nil, |tail,x|List::Cons(x.to_string().parse::<BigInt>().unwrap(),Box::new(tail)));' if reference else ''
    output=('let mut words=Vec::new();let mut rest=output;while let List::Cons(x,tail)=rest {words.push(x.to_string());rest=*tail;}' if reference else 'let words=output.iter().map(ToString::to_string).collect::<Vec<_>>();')
    source=source.replace('fn main() {','fn main() {\n if std::env::args().any(|s|s=="--i2r-batch-v2") {batch_v2_main();return;} ',1)
    return source+r'''
fn batch_v2_main() {
 use std::io::Write;
 let mut deltas=Vec::new();
 for _ in 0..10000 {let t=std::time::Instant::now();let d=t.elapsed().as_nanos();if d>0{deltas.push(d);}}
 deltas.sort();println!("V2_CLOCK {} {}",deltas[0],deltas[deltas.len()/2]);std::io::stdout().flush().unwrap();
 let stdin=std::io::stdin();let mut lines=stdin.lock().lines();
 while let Some(header)=lines.next() {
  let header=header.unwrap();let n:usize=header.strip_prefix("B ").unwrap().parse().unwrap();
  let line=lines.next().unwrap().unwrap();let expected=lines.next().unwrap().unwrap();
  let prepared=(0..n).map(|_| {
   let values:Vec<WIRE>=std::hint::black_box(&line).split_whitespace().map(|s|s.parse().unwrap()).collect();
   CONVERT
   std::hint::black_box(PREPARE)
  }).collect::<Vec<_>>();
  let mut inputs=prepared.into_iter();let mut results=Vec::with_capacity(n);
  let start=std::time::Instant::now();
  for prepared in inputs.by_ref() {results.push(std::hint::black_box(RUN));}
  let elapsed=start.elapsed().as_nanos();
  drop(inputs);
  for result in results {let output=ENCODE; OUTPUT assert_eq!(words.join(" "),expected);}
  println!("V2 {} {}",elapsed,n);std::io::stdout().flush().unwrap();
 }
}
'''.replace('WIRE',wire).replace('CONVERT',convert).replace('PREPARE',prepare).replace('RUN',run).replace('ENCODE',encode).replace('OUTPUT',output)


def ocaml(module):
    return r'''external now : unit -> int64 = "i2r_raw_now"
let () =
 let samples=Array.init 10000 (fun _ -> let a=now () in Int64.sub (now ()) a) in
 Array.sort Int64.compare samples;
 let positive=Array.to_list samples |> List.filter (fun x -> x>0L) in
 Printf.printf "V2_CLOCK %Ld %Ld\n%!" (List.hd positive) samples.(5000);
 try while true do
  let header=read_line () in let n=int_of_string (String.sub header 2 (String.length header-2)) in
  let line=read_line () in let expected=read_line () in
  let prepared=Array.init n (fun _ ->
   let input=List.map (fun s -> Reference.MODULE.nat_of_integer (Z.of_string s))
     (List.filter ((<>) "") (String.split_on_char ' ' (Sys.opaque_identity line))) in
   Sys.opaque_identity (Reference.MODULE.kernel_prepare input)) in
  let results=Array.make n None in
  let start=now () in
  for i=0 to n-1 do results.(i) <- Some (Sys.opaque_identity (Reference.MODULE.kernel_run prepared.(i))) done;
  let elapsed=Int64.sub (now ()) start in
  Array.iter (fun value -> let output=Reference.MODULE.kernel_encode (Option.get value) in
   let actual=String.concat " " (List.map (fun x -> Z.to_string (Reference.MODULE.integer_of_nat x)) output) in
   if actual<>expected then failwith "batch output mismatch") results;
  Printf.printf "V2 %Ld %d\n%!" elapsed n
 done with End_of_file -> ()
'''.replace('MODULE',module)

HASKELL = r'''{-# LANGUAGE ForeignFunctionInterface #-}
module Main where
import qualified Candidate as C
import Control.DeepSeq (force)
import Control.Exception (evaluate)
import Control.Monad (forM_, forM, replicateM, when)
import Data.Array.IO
import Data.Word (Word64)
import Data.List (sort)
import System.IO
foreign import ccall unsafe "i2r_clock_ns" now :: IO Word64
{-# NOINLINE opaque #-}
opaque :: Int -> a -> a
opaque k x = if k<0 then error "negative ticket" else x
main :: IO ()
main = do
 hSetBuffering stdout LineBuffering
 samples <- replicateM 10000 (do a<-now; b<-now; pure (b-a))
 let ticks=sort samples
 putStrLn ("V2_CLOCK "++show (head (filter (>0) ticks))++" "++show (ticks!!5000))
 loop
boxList :: [a] -> IO (IOArray Int a)
boxList xs = newListArray (0,length xs-1) xs
boxEmpty :: Int -> IO (IOArray Int a)
boxEmpty n = newArray_ (0,n-1)
loop :: IO ()
loop = do
 eof<-isEOF
 if eof then pure () else do
  header<-getLine;line<-getLine;expected<-getLine
  let n=read (drop 2 header) :: Int
  prepared<-forM [0..n-1] $ \i -> evaluate (force (C.kernel_prepare (map (C.nat_of_integer . read) (words (opaque i line)))))
  inputs<-boxList prepared
  results<-boxEmpty n
  start<-now
  forM_ [0..n-1] $ \i -> do
   p<-readArray inputs i
   r<-evaluate (force (C.kernel_run p))
   writeArray results i r
  end<-now
  forM_ [0..n-1] $ \i -> do
   r<-readArray results i
   let actual=unwords (map (show . C.integer_of_nat) (C.kernel_encode r))
   when (actual/=expected) (error "batch output mismatch")
  putStrLn ("V2 "++show (end-start)++" "++show n)
  loop
'''

SCALA = r'''object Main {
 def main(args: Array[String]): Unit = {
  val ticks = Array.fill[Long](10000) {val a=System.nanoTime();System.nanoTime()-a}.sorted
  println("V2_CLOCK " + ticks.find(_>0).get + " " + ticks(5000)); Console.out.flush()
  val lines=scala.io.Source.stdin.getLines()
  while(lines.hasNext) {
   val n=lines.next().stripPrefix("B ").toInt
   val line=lines.next();val expected=lines.next()
   val prepared=Array.tabulate(n) {i =>
    Candidate.kernel_prepare(line.split("\\s+").filter(_.nonEmpty).toList.map(s => Candidate.nat_of_integer(BigInt(s))))
   }
   val results=new Array[RESULT](n)
   val start=System.nanoTime();var i=0
   while(i<n) {results(i)=Candidate.kernel_run(prepared(i));i+=1}
   val elapsed=System.nanoTime()-start
   i=0;while(i<n) {
    val actual=Candidate.kernel_encode(results(i)).map(x=>Candidate.integer_of_nat(x).toString).mkString(" ")
    require(actual==expected,"batch output mismatch");i+=1
   }
   println("V2 "+elapsed+" "+n);Console.out.flush()
  }
 }
}
'''


def scala(source):
    result=re.search(r'def kernel_run\(.*?\)\s*:\s*(.*?)\s*=',source,re.S)[1]
    # All generated result types live in Candidate; import names for annotations.
    return SCALA.replace('object Main {','import Candidate._\nobject Main {').replace('RESULT',result)

SML = r'''structure Main = struct
fun main () = let
 val library=Foreign.loadLibrary "@CLOCK@"
 val now=Foreign.buildCall0 (Foreign.getSymbol library "i2r_clock_ns", (), Foreign.cUint64Large)
 val ticks=List.tabulate(10000,fn _ => let val a=now() in now()-a end)
 val minimum=List.foldl (fn (x,a) => if x>0 andalso x<a then x else a) (1000000000:LargeInt.int) ticks
 val _=print ("V2_CLOCK "^LargeInt.toString minimum^" "^LargeInt.toString minimum^"\n")
 val _=TextIO.flushOut TextIO.stdOut
 fun line ()=valOf(TextIO.inputLine TextIO.stdIn)
 fun trim s=String.concatWith " " (String.tokens Char.isSpace s)
 fun loop () = case TextIO.inputLine TextIO.stdIn of NONE => () | SOME header => let
  val n=valOf(Int.fromString(String.extract(header,2,NONE)))
  val text=line();val expected=trim(line())
  val prepared=Array.tabulate(n,fn _ => Candidate.kernel_prepare
    (List.map (fn s => Candidate.nat_of_integer(valOf(IntInf.fromString s))) (String.tokens Char.isSpace text)))
  val results=Array.array(n,NONE)
  fun run i=if i=n then () else (Array.update(results,i,SOME(Candidate.kernel_run(Array.sub(prepared,i))));run(i+1))
  val start=now();val _=run 0;val elapsed=now()-start
  val _=Array.app (fn r => let
    val output=Candidate.kernel_encode(valOf r)
    val actual=String.concatWith " " (List.map (IntInf.toString o Candidate.integer_of_nat) output)
    in if actual=expected then () else raise Fail "batch output mismatch" end) results
  val _=print("V2 "^LargeInt.toString elapsed^" "^Int.toString n^"\n")
  val _=TextIO.flushOut TextIO.stdOut
  in loop() end
 in loop() end
end;
'''

GO = r'''package main
import("bufio";"fmt";"os";"strings";"time";"sort";"strconv"
 C "isabelle/exported/Candidate"
 B "isabelle/exported/Bigint")
func main() {
 ticks:=make([]int64,10000);for i:=range ticks {s:=time.Now();ticks[i]=time.Since(s).Nanoseconds()};sort.Slice(ticks,func(i,j int)bool{return ticks[i]<ticks[j]})
 minimum:=int64(1000000000);for _,x:=range ticks{if x>0 && x<minimum{minimum=x}}
 fmt.Printf("V2_CLOCK %d %d\n",minimum,ticks[len(ticks)/2])
 scanner:=bufio.NewScanner(os.Stdin);scanner.Buffer(make([]byte,4096),64*1024*1024)
 for scanner.Scan() {
  n,err:=strconv.Atoi(strings.TrimPrefix(scanner.Text(),"B "));if err!=nil{panic(err)}
  if !scanner.Scan(){panic("input missing")};line:=scanner.Text()
  if !scanner.Scan(){panic("expected missing")};expected:=scanner.Text()
  prepared:=make([]PREPARED,n)
  for i:=0;i<n;i++ {
   words:=strings.Fields(line);var input C.List[C.Nat]=C.Nil[C.Nat]{}
   for j:=len(words)-1;j>=0;j-- {input=C.Cons[C.Nat]{A:C.Nat_of_integer(B.MkInt(words[j])),Aa:input}}
   prepared[i]=C.Kernel_prepare(input)
  }
  results:=make([]RESULT,n);start:=time.Now()
  for i:=0;i<n;i++ {results[i]=C.Kernel_run(prepared[i])}
  elapsed:=time.Since(start).Nanoseconds()
  for _,r:=range results {
   output:=C.Kernel_encode(r);words:=[]string{}
   for {node,ok:=output.(C.Cons[C.Nat]);if !ok{break};value:=C.Integer_of_nat(node.A);words=append(words,value.String());output=node.Aa}
   if strings.Join(words," ")!=expected{panic("batch output mismatch")}
  }
  fmt.Printf("V2 %d %d\n",elapsed,n)
 }
 if err:=scanner.Err();err!=nil{panic(err)}
}
'''


def go(source):
    prepare=re.search(r'func Kernel_prepare\s*\(.*?\)\s+([^\n]+?)\s*\{',source)[1]
    result=re.search(r'func Kernel_run\s*\(.*?\)\s+([^\n]+?)\s*\{',source)[1]
    def qualify(s):return re.sub(r'\b([A-Z]\w*)\b',r'C.\1',s)
    return GO.replace('PREPARED',qualify(prepare)).replace('RESULT',qualify(result))
