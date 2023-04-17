### DUMMY FUNCTIONS ###

@nopp
# dummy functions if NOT running in ecflow:
# we have to "solve" for ecflow_client commands, but also @include and other macro's
# probably @include will have to be an alias defined in the calling environment
# ??? start every script with [[ $ECF_NAME ]] ... ?
# problem: this will never get the HPC headers in place...
# TODO: how to deal with comments, macro's (@[comment|manual] ... @end, ... in scripts?
#       first attempt: just define as "functions" that are never called
# and "@" of course will have to change anyway
[[ $ECF_NAME ]] || {
  function ecflow_client  { echo No ecFlow client ;}
  alias @include=iinclude
  function iinclude {
    iiff="$*"
    ifile=`echo "$iiff" | cut -d "<" -f2 | cut -d ">" -f1`
    . $BASEDIR/include/$infile
  }
  alias @comment="function xxxxx {"
  alias @macro="function xxxxx {"
  alias @end="}"

}
@end
